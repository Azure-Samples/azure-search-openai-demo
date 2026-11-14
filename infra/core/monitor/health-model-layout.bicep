// ============================================================================
// Health Model - Canvas Layout Functions
// ============================================================================
// Reusable, pure functions that compute the `canvasPosition` {x, y} for Azure
// Monitor Health Model entities. Import them wherever an entity needs a
// position so the layout math lives in ONE place instead of being repeated
// inline on every entity.
//
// How the layout engine works
// ---------------------------
// Entities are arranged in rows by their LEVEL in the use-case tree:
//   - root  -> y = 0            (the health model resource is the implicit root)
//   - group -> y = groupRow     (use-case groups, e.g. "RAG Chat")
//   - leaf  -> y = leafRow       (individual resources under a group)
//
// Horizontally:
//   - Within a group, leaves are placed left-to-right. The Nth leaf (0-based)
//     sits at  x = groupX + N * spacing.
//   - Groups are packed left-to-right. The next group's column starts after the
//     current group's leaves:  nextGroupX = currentGroupX + childCount * spacing.
//     A disabled group has childCount = 0 and therefore contributes no width.
//
// So the whole layout is driven by two pieces of data only:
//   1. how many leaves each group has  (childCount, "entities per level"), and
//   2. each leaf's index within its group.
// Everything else is computed by the functions below.
//
// Bicep note: user-defined functions cannot read file-level `param`s, so the
// spacing and row values are passed in as arguments. This keeps the functions
// pure and importable by any module.
//
// Usage:
//   import { groupPosition, leafPosition, nextGroupX } from './health-model-layout.bicep'
//   ...
//   canvasPosition: leafPosition(xRagChat, 1, canvasLeafSpacing, canvasLeafRow)

@export()
@description('Canvas position for a use-case group entity (the group heads its column).')
func groupPosition(groupX int, groupRow int) object => {
  x: groupX
  y: groupRow
}

@export()
@description('Canvas position for the Nth leaf entity within a group (leftmost leaf is index 0).')
func leafPosition(groupX int, leafIndex int, spacing int, leafRow int) object => {
  x: groupX + leafIndex * spacing
  y: leafRow
}

@export()
@description('X coordinate where the next group column begins, after a group of childCount leaves.')
func nextGroupX(currentGroupX int, childCount int, spacing int) int => currentGroupX + childCount * spacing
