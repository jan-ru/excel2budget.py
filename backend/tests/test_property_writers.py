"""Properties 13–16: Writer behaviour property tests.

Feature: financial-domain-model
Validates: Requirements 3.2, 3.3, 5.1–5.5, 7.3, 7.4

Property 13: Writer output row count matches FinancialDocument lines
Property 14: from_source mapping extracts correct field values
Property 15: period_number transform extracts correct period
Property 16: DC split produces correct debit/credit based on normal_balance
"""

from __future__ import annotations


from hypothesis import given, settings
from hypothesis import strategies as st

from backend.app.core.adapters import financial_document_to_tabular
from backend.app.core.domain import (
    Account,
    AccountType,
    DebitCredit,
    Entity,
    FinancialDocument,
    FinancialLine,
    LineType,
)
from backend.app.core.types import (
    DataType,
    FromSource,
    FromTransform,
    NullVal,
    OutputTemplate,
    TemplateColumnDef,
)
from backend.tests.strategies import (
    account_codes,
    amounts,
    entity_codes,
    financial_lines,
    periods,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _simple_template(*cols: TemplateColumnDef) -> OutputTemplate:
    return OutputTemplate(
        packageName="test",
        templateName="test",
        columns=list(cols),
    )


def _make_doc(
    lines: tuple[FinancialLine, ...],
    accounts: tuple[Account, ...] = (),
    entities: tuple[Entity, ...] = (),
) -> FinancialDocument:
    return FinancialDocument(
        lines=lines,
        accounts=accounts,
        entities=entities,
        meta={},
    )


# ---------------------------------------------------------------------------
# Property 13: Writer output row count matches FinancialDocument lines
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    lines=st.lists(financial_lines, min_size=0, max_size=30).map(tuple),
)
def test_output_row_count_matches_lines(lines: tuple[FinancialLine, ...]) -> None:
    """Property 13: output has exactly N data rows for N lines."""
    doc = _make_doc(lines)
    template = _simple_template(
        TemplateColumnDef(
            name="account",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="account"),
        ),
    )
    result = financial_document_to_tabular(doc, template)
    assert result.rowCount == len(lines)
    assert len(result.rows) == len(lines)


# ---------------------------------------------------------------------------
# Property 14: from_source mapping extracts correct field values
# ---------------------------------------------------------------------------

SOURCE_FIELDS = ["account", "entity", "period", "amount", "line_type", "currency"]


@settings(max_examples=100)
@given(
    line=financial_lines,
    field_name=st.sampled_from(SOURCE_FIELDS),
)
def test_from_source_extracts_correct_value(
    line: FinancialLine,
    field_name: str,
) -> None:
    """Property 14: from_source extracts the named field from the line."""
    doc = _make_doc((line,))
    template = _simple_template(
        TemplateColumnDef(
            name="col",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName=field_name),
        ),
    )
    result = financial_document_to_tabular(doc, template)
    cell = result.rows[0].values[0]
    assert not isinstance(cell, NullVal)

    expected = str(getattr(line, field_name))
    assert cell.value == expected  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Property 15: period_number transform extracts correct period
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(line=financial_lines)
def test_period_number_extracts_month(line: FinancialLine) -> None:
    """Property 15: period_number transform extracts month 1–12 from YYYY-MM."""
    doc = _make_doc((line,))
    template = _simple_template(
        TemplateColumnDef(
            name="period_num",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromTransform(expression="period_number"),
        ),
    )
    result = financial_document_to_tabular(doc, template)
    cell = result.rows[0].values[0]
    assert not isinstance(cell, NullVal)

    # Extract expected month from the period string
    expected_month = int(line.period.split("-")[1])
    assert cell.value == str(expected_month)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Property 16: DC split produces correct debit/credit based on normal_balance
# ---------------------------------------------------------------------------


@st.composite
def line_with_account(draw: st.DrawFn):
    """Generate a FinancialLine with a matching Account for DC split testing."""
    code = draw(account_codes)
    normal_balance = draw(st.sampled_from(DebitCredit))
    account = Account(
        code=code,
        description="test",
        account_type=draw(st.sampled_from(AccountType)),
        normal_balance=normal_balance,
    )
    line = FinancialLine(
        account=code,
        entity=draw(entity_codes),
        period=draw(periods),
        amount=draw(amounts),
        line_type=draw(st.sampled_from(LineType)),
    )
    return line, account


@settings(max_examples=100)
@given(data=line_with_account())
def test_dc_split_correct_column(
    data: tuple[FinancialLine, Account],
) -> None:
    """Property 16: DC split places amount in correct column based on normal_balance."""
    line, account = data

    doc = _make_doc((line,), accounts=(account,))
    template = _simple_template(
        TemplateColumnDef(
            name="debit",
            dataType=DataType.STRING,
            nullable=True,
            sourceMapping=FromTransform(expression="debit"),
        ),
        TemplateColumnDef(
            name="credit",
            dataType=DataType.STRING,
            nullable=True,
            sourceMapping=FromTransform(expression="credit"),
        ),
    )
    result = financial_document_to_tabular(doc, template)
    debit_cell = result.rows[0].values[0]
    credit_cell = result.rows[0].values[1]

    if account.normal_balance == DebitCredit.DEBIT:
        # Amount goes to debit column
        assert not isinstance(debit_cell, NullVal)
        assert debit_cell.value == str(line.amount)  # type: ignore[union-attr]
        assert isinstance(credit_cell, NullVal)
    else:
        # Amount goes to credit column
        assert isinstance(debit_cell, NullVal)
        assert not isinstance(credit_cell, NullVal)
        assert credit_cell.value == str(line.amount)  # type: ignore[union-attr]
