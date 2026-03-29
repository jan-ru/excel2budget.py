"""Property test for OutputTemplate completeness.

**Validates: Requirement 3.3**

Property 17: OutputTemplate completeness — every valid package/template
combination returned by the registry has non-empty columns with defined
names, types, and source mappings.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    DataType,
    FixedNull,
    FromSource,
    FromTransform,
    FromUserParam,
)
from src.templates.registry import (
    getTemplate,
    listPackages,
    listTemplates,
)


def _all_package_template_pairs():
    """Collect every valid (package, template) pair from the registry."""
    pairs = []
    for pkg in listPackages():
        for tmpl in listTemplates(pkg):
            pairs.append((pkg, tmpl))
    return pairs


VALID_SOURCE_MAPPING_TYPES = (FromSource, FromUserParam, FromTransform, FixedNull)
VALID_DATA_TYPES = set(DataType)


@given(data=st.data())
@settings(max_examples=50)
def test_property_17_output_template_completeness(data):
    """Property 17: OutputTemplate completeness.

    **Validates: Requirement 3.3**

    For every valid package/template combination in the registry, the
    returned OutputTemplate has non-empty columns where each column has
    a non-empty name, a valid DataType, and a defined ColumnSourceMapping.
    """
    pairs = _all_package_template_pairs()
    assert len(pairs) > 0, "Registry must contain at least one package/template pair"

    # Use hypothesis to pick a random pair each run
    pair = data.draw(st.sampled_from(pairs), label="package_template_pair")
    pkg, tmpl_name = pair

    template = getTemplate(pkg, tmpl_name)

    # Template must have non-empty columns
    assert len(template.columns) > 0, (
        f"Template '{pkg}/{tmpl_name}' has no columns"
    )

    for i, col in enumerate(template.columns):
        # Every column must have a non-empty name
        assert isinstance(col.name, str) and len(col.name) > 0, (
            f"Column {i} in '{pkg}/{tmpl_name}' has empty or non-string name"
        )

        # Every column must have a valid DataType
        assert col.dataType in VALID_DATA_TYPES, (
            f"Column {i} ('{col.name}') in '{pkg}/{tmpl_name}' has invalid "
            f"dataType: {col.dataType}"
        )

        # Every column must have a defined sourceMapping
        assert isinstance(col.sourceMapping, VALID_SOURCE_MAPPING_TYPES), (
            f"Column {i} ('{col.name}') in '{pkg}/{tmpl_name}' has invalid "
            f"sourceMapping type: {type(col.sourceMapping)}"
        )
