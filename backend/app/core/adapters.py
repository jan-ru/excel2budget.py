"""Adapter layer — bidirectional conversion between TabularData and FinancialDocument.

Enables incremental migration: existing pipeline stages that speak ``TabularData``
can interoperate with new code that speaks ``FinancialDocument``.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from backend.app.core.domain import (
    Account,
    AccountCode,
    AccountType,
    BudgetLine,
    DebitCredit,
    Entity,
    EntityCode,
    FinancialDocument,
    FinancialLine,
)
from backend.app.core.types import (
    CellValue,
    ColumnDef,
    FromSource,
    FromTransform,
    FromUserParam,
    FixedNull,
    MappingConfig,
    NullVal,
    OutputTemplate,
    Row,
    StringVal,
    TabularData,
    UserParams,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cell_to_str(cell: CellValue) -> str:
    """Extract a string representation from any CellValue variant."""
    if isinstance(cell, NullVal):
        return ""
    return str(cell.value)


def _cell_to_decimal(cell: CellValue) -> Decimal:
    """Extract a Decimal from a CellValue, defaulting to 0 for non-numeric."""
    if isinstance(cell, NullVal):
        return Decimal("0")
    try:
        return Decimal(str(cell.value))
    except InvalidOperation:
        return Decimal("0")


def _col_index(columns: list[ColumnDef], name: str) -> int:
    """Return the index of the column named *name*, or raise ValueError."""
    for i, col in enumerate(columns):
        if col.name == name:
            return i
    raise ValueError(f"Column '{name}' not found in tabular data")


# ---------------------------------------------------------------------------
# TabularData → FinancialDocument
# ---------------------------------------------------------------------------


def tabular_to_financial_document(
    data: TabularData,
    mapping: MappingConfig,
    params: UserParams,
) -> FinancialDocument:
    """Convert a ``TabularData`` to a ``FinancialDocument``.

    Each data row is mapped to a ``BudgetLine`` for every month column in the
    mapping config.  ``Account`` and ``Entity`` dimension entries are extracted
    from the unique values found in the data.

    Raises ``ValueError`` when a required column from the mapping config is
    missing from the tabular data.
    """
    columns = data.columns

    # Validate that all mapped columns exist
    entity_idx = _col_index(columns, mapping.entityColumn)
    account_idx = _col_index(columns, mapping.accountColumn)
    dc_idx = _col_index(columns, mapping.dcColumn)

    month_indices: list[tuple[int, int, int]] = []  # (col_idx, period_number, year)
    for mc in mapping.monthColumns:
        idx = _col_index(columns, mc.sourceColumnName)
        month_indices.append((idx, mc.periodNumber, mc.year))

    # Build lines and collect dimension data
    lines: list[BudgetLine] = []
    seen_accounts: dict[str, DebitCredit] = {}
    seen_entities: set[str] = set()

    for row in data.rows:
        vals = row.values
        entity_str = _cell_to_str(vals[entity_idx])
        account_str = _cell_to_str(vals[account_idx])
        dc_str = _cell_to_str(vals[dc_idx]).upper()

        if not account_str:
            continue  # skip rows with empty account

        # Track dimensions
        normal_balance = DebitCredit.DEBIT if dc_str == "D" else DebitCredit.CREDIT
        seen_accounts[account_str] = normal_balance
        seen_entities.add(entity_str)

        for col_idx, period_number, year in month_indices:
            amount = _cell_to_decimal(vals[col_idx])
            period_str = f"{year}-{period_number:02d}"
            lines.append(
                BudgetLine(
                    account=AccountCode(account_str),
                    entity=EntityCode(entity_str),
                    period=period_str,
                    amount=amount,
                    version=params.budgetcode,
                ),
            )

    # Build dimension tuples
    account_objs = tuple(
        Account(
            code=AccountCode(code),
            description=code,
            account_type=AccountType.EXPENSE,
            normal_balance=nb,
        )
        for code, nb in seen_accounts.items()
    )
    entity_objs = tuple(
        Entity(code=EntityCode(code), description=code)
        for code in sorted(seen_entities)
    )

    return FinancialDocument(
        lines=tuple(lines),
        accounts=account_objs,
        entities=entity_objs,
        meta={"source": data.metadata.sourceName},
    )


# ---------------------------------------------------------------------------
# FinancialDocument → TabularData
# ---------------------------------------------------------------------------


def _extract_period_number(period: str) -> int:
    """Extract the month number (1–12) from a ``YYYY-MM`` period string."""
    parts = period.split("-")
    if len(parts) >= 2:
        return int(parts[1])
    return 0


def _resolve_from_source(line: FinancialLine, source_col: str) -> CellValue:
    """Extract a field value from a FinancialLine by field name."""
    field_map: dict[str, str] = {
        "account": line.account,
        "entity": line.entity,
        "period": line.period,
        "amount": str(line.amount),
        "line_type": line.line_type,
        "currency": line.currency,
        "memo": line.memo or "",
    }
    value = field_map.get(source_col)
    if value is None:
        return NullVal()
    return StringVal(value=value)


def _build_account_lookup(doc: FinancialDocument) -> dict[str, Account]:
    """Build a lookup from account code → Account for DC split."""
    return {acct.code: acct for acct in doc.accounts}


def _resolve_dc_split(
    line: FinancialLine,
    expression: str,
    account_lookup: dict[str, Account],
) -> CellValue:
    """Resolve a DC-based transform expression.

    Supported expressions:
    - ``"debit"``: amount if normal_balance is D, else null
    - ``"credit"``: amount if normal_balance is C, else null
    """
    acct = account_lookup.get(line.account)
    if acct is None:
        return NullVal()

    is_debit_normal = acct.normal_balance == DebitCredit.DEBIT

    if expression == "debit":
        if is_debit_normal:
            return StringVal(value=str(line.amount))
        return NullVal()
    elif expression == "credit":
        if not is_debit_normal:
            return StringVal(value=str(line.amount))
        return NullVal()

    return NullVal()


def financial_document_to_tabular(
    doc: FinancialDocument,
    template: OutputTemplate,
) -> TabularData:
    """Convert a ``FinancialDocument`` to a ``TabularData`` using *template*.

    Each ``FinancialLine`` becomes one ``Row``.  Column values are resolved
    from the template's ``ColumnSourceMapping`` entries:

    - ``from_source``: extract the named field from the line
    - ``from_transform``: ``"period_number"`` extracts month; ``"debit"``/``"credit"`` do DC split
    - ``from_user_param``: not resolved here (would need UserParams — emits empty string)
    - ``fixed_null``: always ``NullVal``
    """
    account_lookup = _build_account_lookup(doc)

    # Build column definitions
    col_defs = [
        ColumnDef(name=tc.name, dataType=tc.dataType, nullable=tc.nullable)
        for tc in template.columns
    ]

    rows: list[Row] = []
    for line in doc.lines:
        cells: list[CellValue] = []
        for tc in template.columns:
            mapping = tc.sourceMapping
            if isinstance(mapping, FromSource):
                cells.append(_resolve_from_source(line, mapping.sourceColumnName))
            elif isinstance(mapping, FromTransform):
                if mapping.expression == "period_number":
                    cells.append(
                        StringVal(value=str(_extract_period_number(line.period))),
                    )
                elif mapping.expression in ("debit", "credit"):
                    cells.append(
                        _resolve_dc_split(line, mapping.expression, account_lookup),
                    )
                else:
                    cells.append(NullVal())
            elif isinstance(mapping, FromUserParam):
                # UserParams not available in this direction — emit empty
                cells.append(StringVal(value=""))
            elif isinstance(mapping, FixedNull):
                cells.append(NullVal())
            else:
                cells.append(NullVal())
        rows.append(Row(values=cells))

    return TabularData(
        columns=col_defs,
        rows=rows,
        rowCount=len(rows),
    )
