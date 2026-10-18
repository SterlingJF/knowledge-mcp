# Team conventions

Save team conventions in `<team>/.knowledge-bus/plugins/knowledge-mcp/conventions.yaml`.
knowledge-mcp uses ancestor conventions when a folder has no conventions file. Each saved conventions file creates a boundary.
Each team explicitly selects parent conventions through `from_parent` pairs of universe spec and document type.
The nearest ancestor conventions file supplies parent declarations. Selected declarations cannot pass through another team.

Call `kb_list_conventions` with supplied universe spec configuration and explicit conventions text or absence markers along the ancestor path.
The answer lists complete saved conventions, declaring folders and parent marks.
knowledge-mcp marks automatic declarations inactive when document types are unavailable or universe spec definitions differ.
Invalid explicit selections return a configuration error.

A selected convention keeps the declaring folder as its filing base.
For example, Finance selecting the company `Contracts` convention still proposes the company `Contracts` folder.
Save a local Finance convention to propose `Finance/Contracts`.

Prepare local changes and parent selections through `kb_prepare_conventions` with the target `folder` and ancestor context.
Review the complete resulting list and supply permission before saving replacement YAML.
Reread target text, parent conventions and universe spec configuration before writing. Repeat preparation after saving.
Existing documents move after accepted proposals through `kb_prepare_document_move`, including both preparation calls and link repairs.
