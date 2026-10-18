# Convention templates

Choose ACE, customized ACE, PARA, Johnny.Decimal or a mix for notes.
Codebase records keep their existing structure.
Your agent lists every note document type from the current universe specs and reads each purpose before proposing conventions.

| Pattern        | Folders                                                    | Naming suggestion                                                                   |
| -------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| ACE            | Atlas for knowledge, Calendar for time, Efforts for action | Title; recorded date alone for daily notes; date and title for other Calendar notes |
| PARA           | Projects, Areas, Resources, Archives                       | Title; optional subfolders from recorded project, area or topic properties          |
| Johnny.Decimal | Supplied numbered area, category and ID folders            | Recorded date and title, directly inside an ID folder                               |

ACE and PARA prescribe folder purposes, without filename rules.
knowledge-mcp suggests title naming and meeting-note filenames.
The daily-note suggestion follows Obsidian daily notes.
Your agent confirms the actual date property before acceptance and asks for missing values.
Johnny.Decimal numbers come from your existing structure or your supplied folder names.
Your agent checks category and ID membership and asks for corrections before saving an invalid hierarchy.

## Customize and combine

Keep exact folder names such as `Atlas (ai-owned)`, `Atlas (general notes)` and `Efforts (time-bound notes)`.
Confirm each document-type assignment and choose folders for daily and meeting notes explicitly.
Folder spelling alone cannot establish authorship.
For one document type spanning several folders, choose a single folder or use a reviewed property containing the folder name.

Combine ACE daily notes, PARA project notes and numbered decision records in the same conventions file.
For example, a recorded `decision_number: "0042"` and title “Use a shared cache” produce `Atlas/Decisions/0042 Use a shared cache.md`.
Your agent asks for missing numbers and allocates no sequence numbers.

## Review and save

1. Review a proposal or a specific question for every note document type.
2. Check the existing convention, proposed folder, naming parts, value sources and rendered example.
3. Check folders marked new, including an agent check for existing empty folders.
4. Accept, change or drop each proposal. Dropped proposals preserve existing conventions.
5. Let your agent save accepted conventions after checking for concurrent changes.
6. Review file moves separately. Saving conventions leaves existing names, folders and classifications unchanged.

The catalog ships with knowledge-mcp and loads offline.
Saved conventions contain accepted patterns and remain unchanged when template definitions change.
The shared workflow serves Claude Code, Codex, the Claude desktop app, Pi and OpenCode.

## Sources

- Nick Milo: [ACE folder framework](https://blog.linkingyourthinking.com/notes/ace-folder-framework), [expansion and contraction](https://blog.linkingyourthinking.com/notes/the-ace-folder-framework-flexes-for-you), [detailed structure](https://blog.linkingyourthinking.com/notes/a-deeper-dive-into-how-ace-works).
- Obsidian: [Daily notes](https://obsidian.md/help/plugins/daily-notes).
- Tiago Forte: [The PARA Method](https://fortelabs.com/blog/para/).
- Johnny.Decimal: [Numbers](https://johnnydecimal.com/documentation/the-numbers), [IDs](https://johnnydecimal.com/documentation/ids), [saving files](https://johnnydecimal.com/documentation/saving-files), [naming files](https://johnnydecimal.com/documentation/naming-files).
- Michael Nygard: [Decision records](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
