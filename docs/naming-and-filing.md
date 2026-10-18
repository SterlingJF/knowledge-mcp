# Naming and filing conventions

You can set a naming convention and a filing convention for each document type in your universe specs. knowledge-mcp reads the conventions that apply in a file's folder and proposes a name and a folder for the file. Your agent moves and renames the file once you accept. This page covers starting from a template, writing your own conventions, nesting conventions across teams and folders, seeing which conventions apply where, and the work your agent does with the conventions.

## From file to proposal

1. Your agent identifies the file's document type from the file name and folder, and reads the content whenever your agent cannot tell the document type from the name and folder alone.
2. knowledge-mcp looks up the naming and filing conventions that apply to that document type in the file's folder.
3. knowledge-mcp proposes a name and a folder.
4. Your agent shows you the proposal. Once you accept, your agent moves and renames the file through its own access to the store and updates every link to the file.
5. knowledge-mcp keeps the file's document type in the new folder.

## Start from a template

Choose a template, and knowledge-mcp proposes a naming convention and a filing convention for each document type in your universe specs. You accept, change or drop each proposed convention before any file moves.

The templates below suit a knowledge base of notes, not a codebase. Codebase records keep the folders the codebase already uses.

- **ACE (Atlas, Calendar, Efforts):** in Nick Milo's folder system, Atlas holds knowledge, Calendar holds time and Efforts holds action. The template assigns each document type to one of the three folders and names Calendar notes date first, in year-month-day order.
- **A customized ACE:** keep your own folder names, such as an Atlas split into notes your agent writes and notes you write, and the template follows your folders.
- **PARA (Projects, Areas, Resources, Archives):** in Tiago Forte's system, you sort information by actionability into four folders. The template assigns each document type to Projects, Areas, Resources or Archives.
- **Johnny.Decimal:** in Johnny Noble and Lucy Butcher's system, you number areas, categories and IDs, keep files only in ID folders and start file names with the date. The template keeps the same numbers and date-first names.
- **A mix:** combine patterns, for example ACE folders with decision records numbered in order in one folder.

## Start from the folders you already keep

When your folders already hold files of a document type, knowledge-mcp proposes a filing convention from those folders. Accept the proposal to keep your current structure as the convention.

## Write your own conventions

For each document type, a convention names the folder and the parts of the file name.

- **Fixed parts:** the document type, a date or a property recorded in the document, such as a project code.
- **A value from the content:** your agent reads one value from the document, such as the title, the client or another party, and places the value in the name or the folder.

### Examples

- **Meeting notes:** filed in Calendar and named by date, then title.
- **Decision records:** filed in one folder and numbered in order, with numbers never reused, following Michael Nygard's published practice.
- **Invoices:** filed in the client's folder and named by date and client.

Change, add or remove a convention whenever the work changes. Files already in place keep their names and folders until you accept a new proposal, one file at a time or a whole folder in one list.

## Conventions across teams and folders

Conventions nest the same way universe specs nest.

- Conventions for the whole knowledge base apply in every folder below, except a team folder that keeps its own conventions.
- A team or department can keep its own conventions in its folder, and then takes from the parent folder only what the team chooses.
- The parent folder is the nearest folder above that keeps its own conventions.

For example, a village hall keeps conventions for hall bookings and hall upkeep in its top folder. The management committee keeps conventions for its minutes in the committee folder and takes the hall upkeep conventions from the parent folder, because the committee signs off hirer checklists.

In a company, the finance team keeps conventions for invoices in its folder and takes the contract conventions from the company folder, because the finance team also files signed contracts.

## Conventions in effect for a folder

Ask your agent which conventions apply in any folder. The answer lists each convention by document type, names the folder each convention comes from and labels each convention taken from the parent folder.

## Teams that use words differently

Each team keeps its own terms, each with one meaning, in its folder beside its own document types and conventions. In a team folder, knowledge-mcp builds each proposal from the team's own document types and conventions, so two teams can file the same document type in different folders on purpose, with both conventions visible.

## Review many files at once

Your agent can show every proposal for a folder in one list. Drop or change any row, then accept the list in one step, and your agent makes every move and rename on the list.

## Your agent's part

- Your agent gets the conventions that apply in a file's folder whenever your agent works on the file, in every session and every chat.
- When a file could belong to more than one document type, the document types for your role come first, and your agent asks you to confirm the document type.
- Each proposal names the document type, the convention behind the proposal and the folder the convention comes from.
- When a proposed folder does not exist yet, the proposal marks the folder as new, and your agent creates the folder with the move once you accept.
- Your agent moves or renames a file only on your request, an accepted proposal or a standing instruction you wrote for your agent.
- knowledge-mcp proposes, and your agent makes every move.

## Files with no convention

- A document type without a convention gets a folder proposed from the folders already holding files of that document type, and you can keep the proposal as a convention.
- A file with no document type stays where it is, under its current name, and comes up among the files that still need a document type when a session starts.
- When files with no document type keep arriving, ask your agent to add a document type to a universe spec with the knowledge-bus skills that ship with knowledge-mcp; each proposed change shows its evidence and waits for your answer.

## Sources

- Nick Milo: [ACE folder framework](https://blog.linkingyourthinking.com/notes/ace-folder-framework), [expansion and contraction](https://blog.linkingyourthinking.com/notes/the-ace-folder-framework-flexes-for-you), [detailed structure](https://blog.linkingyourthinking.com/notes/a-deeper-dive-into-how-ace-works).
- Obsidian: [Daily notes](https://obsidian.md/help/plugins/daily-notes).
- Tiago Forte: [The PARA Method](https://fortelabs.com/blog/para/).
- Johnny.Decimal: [Numbers](https://johnnydecimal.com/documentation/the-numbers), [IDs](https://johnnydecimal.com/documentation/ids), [saving files](https://johnnydecimal.com/documentation/saving-files), [naming files](https://johnnydecimal.com/documentation/naming-files).
- Michael Nygard: [Decision records](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
