# Wireframes

Primary artifact:

- `docs/wireframes/veggieai_frontend_wireframe.xml` (manifest)

Per-page XML files:

- `docs/wireframes/global_shell_wireframe.xml`
- `docs/wireframes/home_wireframe.xml`
- `docs/wireframes/auth_wireframe.xml`
- `docs/wireframes/predict_wireframe.xml`
- `docs/wireframes/prices_wireframe.xml`
- `docs/wireframes/profile_wireframe.xml`
- `docs/wireframes/history_wireframe.xml`

Quick ASCII previews:

## Login
```
+--------------------------------------+
| DOAA MLOps Studio                     |
|                                      |
|  [ Username         ]                |
|  [ Password         ]                |
|  [ Sign In ]                          |
+--------------------------------------+
```
**Rationale**: minimal, focused authentication flow with fast entry and clear CTA.

## Predict
```
+----------------------------------------------------------+
| Prediction Console                   [Model Dropdown]    |
+------------------------------+---------------------------+
| Drag/drop or browse          | Prediction Summary        |
| [Image preview]              | Top-1 label/confidence    |
| Webcam preview + Capture     | Top-k bars + latency      |
| Notes (optional)             |                           |
| [Run Prediction]             |                           |
+------------------------------+---------------------------+
```
**Rationale**: left-to-right flow from input to results, immediate feedback.

## History
```
+----------------------------------------------------------+
| Prediction History     Search: [label:happy model:a]     |
+-----------+----------------------------------------------+
| Filters   | Table (time, model, label, conf, latency, ...) |
| - Date    | [row][row][row]                              |
| - Model   | Pagination controls                          |
| - Label   |                                              |
+-----------+----------------------------------------------+
```
**Rationale**: analytics dashboard layout with a dedicated filter column.

## About
```
+----------------------------------------------------------+
| About + Architecture Snapshot                            |
| [ASCII diagram + summary bullets]                        |
+----------------------------------------------------------+
```
**Rationale**: concise project summary for assessors and demo flow.
