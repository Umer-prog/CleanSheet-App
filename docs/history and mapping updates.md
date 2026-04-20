# Requirements: Extended History & Orphan Dimension Deletion

## Overview

Two related features need to be implemented together:

1. **Extend snapshot history to cover dimension tables and mapping definitions**, so reverting to a previous snapshot fully restores the entire project state — not just transaction data.
2. **Allow deletion of a dimension source that has become orphaned** (i.e., has no active mappings in the current commit), as a narrow exception to the general rule that dimension sources cannot be deleted.

---

## Feature 1: Extended Snapshot History

### Current behaviour

Snapshots currently capture only transaction table data. Reverting restores that data but leaves dimension tables and mapping definitions at their present state, which can be inconsistent with the restored transaction data.

### Required behaviour

Every snapshot must capture the complete project state at the moment it is taken, including:

- All transaction table data (existing behaviour — unchanged)
- All dimension table data as it exists at snapshot time
- The full mapping registry — every defined mapping pair between transaction columns and dimension columns

When a user reverts to a snapshot, all three of the above are restored together. After a successful revert:

- Transaction tables reflect the snapshot state
- Dimension tables reflect the snapshot state
- The mapping registry reflects the snapshot state — including any mappings that were added or removed between now and then

### Snapshot limits and cleanup

The existing limits (maximum 10 snapshots, orphan file cleanup on each new save) apply to the expanded snapshot bundle. When a snapshot is pruned, its transaction data, dimension data, and mapping registry are all cleaned up together.
now make the commit limit to 30

### History/Revert UI

The History panel must make clear that reverting restores all three components. The confirmation step before a revert should communicate that mappings and dimension data will also be rolled back, not just transaction data.

---

## Feature 2: Orphan Dimension Deletion

### Background

The general rule is that dimension sources are not deletable. This exception applies in one specific case only.

### Definition of orphaned

A dimension source is considered orphaned when, in the **current commit state**, zero active mapping pairs reference any column in that dimension table. If at least one mapping still points to that dimension table, it is not orphaned and the general deletion prohibition applies.

### Required behaviour

After any mapping deletion, the system evaluates whether the dimension source that was referenced by the deleted mapping has become orphaned.

If a dimension source is orphaned:

- The Dimension Sources panel surfaces a delete option for that specific source. This option must not appear for dimension sources that still have active mappings.
- The delete option should be visable so the user understands it is a destructive, irreversible action.
- Before executing the deletion, the user is shown a confirmation prompt that makes clear the dimension table and its data will be permanently removed from the project.
- On confirmation, the dimension source and all its associated data are removed from the project.

If the user adds a new mapping that references the previously-orphaned dimension source before deleting it, the delete option must disappear — the source is no longer orphaned.

### Scope of deletion

Deleting an orphaned dimension source removes:

- The dimension source entry itself
- All stored dimension table data for that source
- Any historical snapshot references to that source (i.e., future reverts will not attempt to restore a dimension source that has been explicitly deleted)

### What is not affected

Deleting an orphaned dimension source does not trigger a new snapshot. It does not affect transaction tables. It does not affect other dimension sources or their mappings.

---

## Interaction Between the Two Features

When a user reverts to a snapshot and a dimension source present in that snapshot was subsequently deleted as an orphan, the revert should surface a warning rather than silently failing or partially restoring. The warning should inform the user that one or more dimension sources from the selected snapshot no longer exist and ask them to confirm or cancel the revert.

This edge case should be handled gracefully — the system must not attempt to restore data for a dimension source that the user has explicitly deleted.

---

## Out of Scope

- Deleting a dimension source for any reason other than it being orphaned
- Partial reverts (reverting only transaction data or only mappings)
- Reverting a deletion of an orphaned dimension source