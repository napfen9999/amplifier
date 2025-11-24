# Architecture Notes and TODOs

## Critical Issues to Resolve

### 1. Scope/AttributeType Properties vs. Relationships

**Issue**: Conflict between V3 architecture specification and current implementation

**Current Implementation** (models.py):
- `scope` is a required property on MetaAttributeV3
- `attributeType` is a required property on MetaAttributeV3

**V3 Architecture Specification** (BRAND_COMPOSER_ACTION.md):
- `layer` should be derived via HAS_ATTRIBUTE relationship from Layer node, NOT stored as property
- `scope` should be determined via relationship hierarchy: MetaScope → Layer → MetaAttribute

**Recommendation**:
- Remove `scope` from MetaAttributeV3 model
- Keep `attributeType` as it describes the content type (enumeration/free_text/mixed)
- Derive scope/layer information from graph traversal when needed

**Impact**:
- Models need to be updated
- Database write operations need to handle relationships correctly
- Validation logic may need adjustment

### 2. Test Environment

**Current State**:
- Tests work without database credentials (expected)
- Using model_construct() for invalid test cases to bypass Pydantic validation
- All imports fixed to use absolute imports (not relative)

**TODO**:
- Add integration tests with actual database connection
- Test with real Neo4j instances when credentials available