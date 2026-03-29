# API Reference

The backend auto-generates an OpenAPI spec from Pydantic model definitions, served at `/openapi.json`.

## Endpoints

### Templates

| Endpoint | Method | Response | Description |
|---|---|---|---|
| `/api/templates/packages` | GET | `PackageListResponse` | List available accounting package names |
| `/api/templates/packages/{package}/templates` | GET | `TemplateListResponse` | List template names for a package |
| `/api/templates/packages/{package}/templates/{template}` | GET | `OutputTemplateResponse` | Full template definition with column mappings |

### Documentation

| Endpoint | Method | Request | Response | Description |
|---|---|---|---|---|
| `/api/documentation/generate` | POST | `ApplicationContext` | `DocumentationPack` | Generate all 7 documentation artifacts |

The `ApplicationContext` contains only metadata and aggregates — no raw financial data.

### Configurations

| Endpoint | Method | Description |
|---|---|---|
| `/api/configurations` | GET | List all saved configurations |
| `/api/configurations` | POST | Create a new configuration |
| `/api/configurations/{name}` | GET | Get configuration by name |
| `/api/configurations/{name}` | PUT | Update a configuration |
| `/api/configurations/{name}` | DELETE | Delete a configuration (204) |

### Observability

| Endpoint | Method | Description |
|---|---|---|
| `/openapi.json` | GET | Auto-generated OpenAPI specification |
| `/metrics` | GET | Prometheus metrics (request count, latency, in-progress) |

## Error Handling

All responses use consistent JSON structure:

| Status Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created (configuration) |
| 204 | Deleted (no content) |
| 400 | Client error (incomplete/invalid request) |
| 404 | Not found (includes available options in error detail) |
| 409 | Conflict (duplicate configuration name) |
| 422 | Validation error (malformed request body) |
| 500 | Server error |

Error responses include a `detail` field with a descriptive message. Template 404 errors additionally include `available_packages` or `available_templates` lists.
