/**
 * Rules for computing "Attention Needed" items from syllabus data.
 */

import { YearAdmin, BlockAdmin, ThemeAdmin } from "@/lib/api";

export interface AttentionItem {
  id: string;
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
}

/**
 * Compute attention items from syllabus data.
 */
export function computeAttentionItems(
  years: YearAdmin[],
  blocks: BlockAdmin[],
  themes: ThemeAdmin[],
): AttentionItem[] {
  const items: AttentionItem[] = [];

  // Rule 1: Active year with 0 blocks
  for (const year of years) {
    if (year.is_active) {
      const yearBlocks = blocks.filter((b) => b.year_id === year.id && b.is_active);
      if (yearBlocks.length === 0) {
        items.push({
          id: `year-no-blocks-${year.id}`,
          title: `No blocks in ${year.name}`,
          description: `The year "${year.name}" is active but has no active blocks.`,
          actionLabel: "Manage Syllabus",
          actionHref: "/admin/syllabus",
        });
      }
    }
  }

  // Rule 2: Active block with 0 themes
  for (const block of blocks) {
    if (block.is_active) {
      const blockThemes = themes.filter((t) => t.block_id === block.id && t.is_active);
      if (blockThemes.length === 0) {
        items.push({
          id: `block-no-themes-${block.id}`,
          title: `No themes in ${block.code}`,
          description: `The block "${block.code}" (${block.name}) is active but has no active themes.`,
          actionLabel: "Manage Syllabus",
          actionHref: "/admin/syllabus",
        });
      }
    }
  }

  // Rule 3: Inactive year with active content (optional, simplified)
  for (const year of years) {
    if (!year.is_active) {
      const yearBlocks = blocks.filter((b) => b.year_id === year.id && b.is_active);
      if (yearBlocks.length > 0) {
        items.push({
          id: `inactive-year-active-content-${year.id}`,
          title: `Inactive year has active content`,
          description: `The year "${year.name}" is inactive but contains ${yearBlocks.length} active block(s).`,
          actionLabel: "Manage Syllabus",
          actionHref: "/admin/syllabus",
        });
      }
    }
  }

  return items;
}
