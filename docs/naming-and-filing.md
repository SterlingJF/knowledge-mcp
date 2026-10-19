# Naming and filing conventions

Set naming and filing conventions for the document types in your universe specs. knowledge-mcp uses the conventions for a file's folder to propose a name and folder. Your agent shows the proposal and applies the move once you accept.

## From file to proposal

1. Your agent identifies the document type from the file name, folder and, when needed, content.
2. Your agent supplies the folder's conventions and any values the name needs, such as a recorded date or title.
3. knowledge-mcp proposes a name and a folder.
4. Your agent shows you the proposal, prepares the move and link repairs with knowledge-mcp, then applies the accepted changes with its own file tools.
5. Your agent saves the prepared document-types update, preserving the file's classification after the move.

## Start from a template

Choose a template, and your agent uses its bundled definitions to propose naming and filing conventions for each note document type. You accept, change or drop each proposed convention before any file moves.

The templates below suit a knowledge base of notes, not a codebase. Codebase records keep the folders the codebase already uses.

- **ACE (Atlas, Calendar, Efforts):** in Nick Milo's folder system, Atlas holds knowledge, Calendar holds time and Efforts holds action. Your agent proposes a folder by document purpose. knowledge-mcp adds naming suggestions: daily notes use their recorded date, as in Obsidian, and other Calendar notes use date then title.
- **A customized ACE:** keep your own folder names, such as an Atlas split into notes your agent writes and notes you write, and your agent adapts the proposals to those folders.
- **PARA (Projects, Areas, Resources, Archives):** in Tiago Forte's system, you sort information by actionability into four folders. Your agent proposes a folder by purpose, with project, area or topic subfolders from recorded properties.
- **Johnny.Decimal:** in Johnny Noble and Lucy Butcher's system, you number areas, categories and IDs, keep files only in ID folders and start file names with the date. Your agent preserves supplied numbers and proposes date-first names; it asks for missing numbers rather than allocating them.
- **A mix:** combine patterns, for example ACE folders with decision records numbered in order in one folder.

## Start from the folders you already keep

When your folders already hold files of a document type, knowledge-mcp proposes a filing convention from those folders. Accept the proposal to keep your current structure as the convention.

## Write your own conventions

For each document type, a convention names the folder and the parts of the file name.

- **Literals and recorded values:** fixed text, the document type, a recorded date or a property such as a project code.
- **A value from the content:** your agent reads one value from the document, such as the title, the client or another party, and places the value in the name or the folder.

### Examples

- **Meeting notes:** filed in Calendar and named by date, then title.
- **Decision records:** filed in one folder and numbered in order, following Michael Nygard's published practice. Your agent uses recorded numbers and checks the history to avoid reusing a number; knowledge-mcp does not allocate numbers.
- **Invoices:** filed in the client's folder and named by date and client.

Change, add or remove a convention whenever the work changes. Files already in place keep their names and folders until you accept a new proposal, one file at a time or a whole folder in one list.

## Conventions across teams and folders

Conventions apply by folder. A team with its own conventions chooses which conventions to retain from its parent.

- Conventions for the whole knowledge base apply in every folder below, except a team folder that keeps its own conventions.
- A team or department with its own conventions selects each parent convention explicitly. A selected convention still files relative to the folder where it was declared.
- The parent folder is the nearest folder above that keeps its own conventions.

For example, a village hall keeps conventions for hall bookings and hall upkeep in its top folder. The management committee keeps conventions for its minutes in the committee folder and takes the hall upkeep conventions from the parent folder, because the committee signs off hirer checklists.

In a company, the finance team keeps conventions for invoices in its folder and takes the contract conventions from the company folder, because the finance team also files signed contracts.

## Conventions in effect for a folder

Ask your agent which conventions apply in any folder. The answer lists each convention by document type, names the folder each convention comes from and labels each convention taken from the parent folder.

## Teams that use words differently

Each team keeps its own terms, each with one meaning, in its folder beside its own document types and conventions. In a team folder, knowledge-mcp builds each proposal from the team's own document types and conventions, so two teams can file the same document type in different folders on purpose, with both conventions visible.

## Review many files at once

Ask your agent to review a folder, including subfolders when you want them included. Your agent shows the complete proposal list, with missing values and blocked moves. Drop or change any row, then accept the remaining list together.

knowledge-mcp prepares the moves together so links between the moving notes stay valid. Your agent applies and records the changes. Undo restores the whole list only when the files are unchanged since the move and every required edit was recorded; otherwise it lists the files that need review.

## Keep links working

Moves preserve Markdown links and Obsidian wikilinks, including embeds and links to headings or blocks. Your agent checks notes throughout the knowledge base, including notes outside the folder under review. knowledge-mcp prepares the link repairs, and your agent verifies the targets after applying them.

The move waits if the link search is incomplete, a target is unclear, a destination is occupied or the destination has incompatible document types. Unsupported internal links need correction before the move can proceed. Your agent resolves these problems and checks for changed files before applying the move. If a write fails, recovery leaves other sessions' later edits intact and lists any files that still need attention.

## Your agent's part

- The included writing and tracking skills tell your agent to read the applicable conventions before work and at session start.
- When a file could belong to more than one document type, the document types for your role come first, and your agent asks you to confirm the document type.
- Each proposal names the document type, the convention behind the proposal and the folder the convention comes from.
- When a proposed folder does not exist yet, the proposal marks the folder as new, and your agent creates the folder with the move once you accept.
- Your agent moves or renames a file only on your request, an accepted proposal or a standing instruction you wrote for your agent.
- knowledge-mcp logs its answers in the state folder; your agent applies file changes and records edits for review or undo.

## Files with no convention

- A document type without a convention gets a folder proposed from the folders already holding files of that document type, and you can keep the proposal as a convention.
- A file with no document type stays where it is, under its current name, and appears in the files that still need a document type during the agent's session-start review.
- When files with no document type keep arriving, ask your agent to add a document type to a universe spec with the knowledge-bus skills that ship with knowledge-mcp; each proposed change shows its evidence and waits for your answer.

## Sources

- Nick Milo: [ACE folder framework](https://blog.linkingyourthinking.com/notes/ace-folder-framework), [expansion and contraction](https://blog.linkingyourthinking.com/notes/the-ace-folder-framework-flexes-for-you), [detailed structure](https://blog.linkingyourthinking.com/notes/a-deeper-dive-into-how-ace-works).
- Obsidian: [Daily notes](https://obsidian.md/help/plugins/daily-notes).
- Tiago Forte: [The PARA Method](https://fortelabs.com/blog/para/).
- Johnny.Decimal: [Numbers](https://johnnydecimal.com/documentation/the-numbers), [IDs](https://johnnydecimal.com/documentation/ids), [saving files](https://johnnydecimal.com/documentation/saving-files), [naming files](https://johnnydecimal.com/documentation/naming-files).
- Michael Nygard: [Decision records](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
