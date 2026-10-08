# Upstream

Vendored read-only from [SterlingJF/knowledge-bus](https://github.com/SterlingJF/knowledge-bus). Do not edit these files here; change them upstream, then run `just refresh_knowledge_model <ref>`.

| File                                       | Path when vendored                                     |
| ------------------------------------------ | ------------------------------------------------------ |
| `Knowledge Bus Protocol (KBP).yaml`        | `spec/knowledge-bus-protocol.yaml`                     |
| `Artifact Universe.kbp.yaml`               | `universes/product-development/universe.kbp.yaml`      |
| `Artifact Universe.type-guidance.kbp.yaml` | `universes/product-development/type-guidance.kbp.yaml` |

The engine loads every `*.kbp.yaml` file here. `km-server` bundles this folder as `knowledge-model/`.

## Ref and Date

Not recorded. The next `just refresh_knowledge_model <ref>` records the ref and the date.

The vendored files declare version `0.5`.

| File                                       | SHA-256                                                            |
| ------------------------------------------ | ------------------------------------------------------------------ |
| `Knowledge Bus Protocol (KBP).yaml`        | `205ae7f595685ba70a4a7835a0f064657d899104aecc11922d806c278eed1cec` |
| `Artifact Universe.kbp.yaml`               | `065a857655b2ba7d964b11bcc7d6c15a17342e063c8e2573d8d11f996563838e` |
| `Artifact Universe.type-guidance.kbp.yaml` | `41eda0d2b4d02cea6cfcdfd19d66db8c92d879493f563c25b62f5085c437881d` |
