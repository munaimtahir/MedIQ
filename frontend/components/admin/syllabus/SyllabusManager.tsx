"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAdminYears, useAdminBlocks, useAdminThemes } from "@/lib/admin/syllabus/hooks";
import { useReorderYears, useReorderBlocks, useReorderThemes } from "@/lib/admin/syllabus/hooks";
import { useCrudYear, useCrudBlock, useCrudTheme } from "@/lib/admin/syllabus/hooks";
import { YearAdmin, BlockAdmin, ThemeAdmin } from "@/lib/api";
import { ColumnHeader } from "./ColumnHeader";
import { EntityRow } from "./EntityRow";
import { EmptyState } from "./EmptyState";
import { InlineError } from "./InlineError";
import { ReorderableList } from "./ReorderableList";
import { EditYearDialog, EditBlockDialog, EditThemeDialog } from "./EditEntityDialog";
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog";

export function SyllabusManager() {
  // Data hooks
  const { years, loading: yearsLoading, error: yearsError, refetch: refetchYears } = useAdminYears();
  const [selectedYearId, setSelectedYearId] = useState<number | null>(null);
  const { blocks, loading: blocksLoading, error: blocksError, refetch: refetchBlocks } = useAdminBlocks(selectedYearId);
  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(null);
  const { themes, loading: themesLoading, error: themesError, refetch: refetchThemes } = useAdminThemes(selectedBlockId);

  // Reorder hooks
  const { reorderYears } = useReorderYears();
  const { reorderBlocks } = useReorderBlocks();
  const { reorderThemes } = useReorderThemes();

  // CRUD hooks
  const { createYear, updateYear, toggleYear } = useCrudYear();
  const { createBlock, updateBlock, toggleBlock } = useCrudBlock();
  const { createTheme, updateTheme, toggleTheme } = useCrudTheme();

  // Dialog states
  const [yearDialogOpen, setYearDialogOpen] = useState(false);
  const [editingYear, setEditingYear] = useState<YearAdmin | null>(null);
  const [blockDialogOpen, setBlockDialogOpen] = useState(false);
  const [editingBlock, setEditingBlock] = useState<BlockAdmin | null>(null);
  const [themeDialogOpen, setThemeDialogOpen] = useState(false);
  const [editingTheme, setEditingTheme] = useState<ThemeAdmin | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingEntity, setDeletingEntity] = useState<{
    type: "year" | "block" | "theme";
    id: number;
    name: string;
  } | null>(null);

  // Auto-select first year/block
  useEffect(() => {
    if (years.length > 0 && (selectedYearId === null || selectedYearId === undefined || selectedYearId === 0)) {
      const firstYear = years[0];
      if (firstYear && typeof firstYear.id === "number" && !isNaN(firstYear.id) && firstYear.id > 0) {
        setSelectedYearId(firstYear.id);
      }
    }
  }, [years, selectedYearId]);

  useEffect(() => {
    if (blocks.length > 0 && !selectedBlockId) {
      setSelectedBlockId(blocks[0].id);
    } else if (blocks.length === 0) {
      setSelectedBlockId(null);
    }
  }, [blocks, selectedBlockId]);

  // Handlers
  const handleCreateYear = async (data: { name: string; order_no: number; is_active: boolean }) => {
    await createYear(data);
    await refetchYears();
  };

  const handleUpdateYear = async (data: { name: string; order_no: number; is_active: boolean }) => {
    if (!editingYear) return;
    await updateYear(editingYear.id, data);
    await refetchYears();
  };

  const handleCreateBlock = async (data: { year_id: number; code: string; name: string; order_no: number; is_active: boolean }) => {
    await createBlock(data);
    await refetchBlocks();
  };

  const handleUpdateBlock = async (data: { year_id: number; code: string; name: string; order_no: number; is_active: boolean }) => {
    if (!editingBlock) return;
    await updateBlock(editingBlock.id, data);
    await refetchBlocks();
  };

  const handleCreateTheme = async (data: { block_id: number; title: string; order_no: number; description?: string; is_active: boolean }) => {
    await createTheme(data);
    await refetchThemes();
  };

  const handleUpdateTheme = async (data: { block_id: number; title: string; order_no: number; description?: string; is_active: boolean }) => {
    if (!editingTheme) return;
    await updateTheme(editingTheme.id, data);
    await refetchThemes();
  };

  const handleDelete = async () => {
    if (!deletingEntity) return;
    // Note: Backend may not have DELETE endpoints - using disable as fallback
    // If DELETE endpoints exist, implement them here
    try {
      if (deletingEntity.type === "year") {
        await toggleYear(deletingEntity.id, false);
        await refetchYears();
      } else if (deletingEntity.type === "block") {
        await toggleBlock(deletingEntity.id, false);
        await refetchBlocks();
      } else if (deletingEntity.type === "theme") {
        await toggleTheme(deletingEntity.id, false);
        await refetchThemes();
      }
    } catch {
      // Error handled in hook
    }
  };

  const handleReorderYears = async (orderedIds: number[]) => {
    const success = await reorderYears(orderedIds);
    if (success) {
      await refetchYears();
    }
  };

  const handleReorderBlocks = async (orderedIds: number[]) => {
    if (!selectedYearId) return false;
    const success = await reorderBlocks(selectedYearId, orderedIds);
    if (success) {
      await refetchBlocks();
    }
    return success;
  };

  const handleReorderThemes = async (orderedIds: number[]) => {
    if (!selectedBlockId) return false;
    const success = await reorderThemes(selectedBlockId, orderedIds);
    if (success) {
      await refetchThemes();
    }
    return success;
  };

  const selectedYear = years.find((y) => y.id === selectedYearId);
  const selectedBlock = blocks.find((b) => b.id === selectedBlockId);

  // Desktop: 3 columns, Mobile: tabs
  return (
    <div className="space-y-4">
      {/* Desktop: 3-column layout */}
      <div className="hidden md:grid md:grid-cols-3 gap-4">
        {/* Years Column */}
        <Card className="flex flex-col h-[calc(100vh-12rem)]">
          <ColumnHeader
            title="Years"
            description="Academic years"
            onAdd={() => {
              setEditingYear(null);
              setYearDialogOpen(true);
            }}
            addLabel="Add Year"
          />
          <CardContent className="flex-1 overflow-y-auto">
            {yearsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : yearsError ? (
              <InlineError message={yearsError.message} onRetry={refetchYears} />
            ) : years.length === 0 ? (
              <EmptyState
                title="No years"
                description="Create your first academic year"
                actionLabel="Add Year"
                onAction={() => {
                  setEditingYear(null);
                  setYearDialogOpen(true);
                }}
              />
            ) : (
              <ReorderableList
                items={years}
                onReorder={handleReorderYears}
                renderItem={(year) => (
                  <EntityRow
                    id={year.id}
                    title={year.name}
                    subtitle={`Order: ${year.order_no}`}
                    isActive={year.is_active}
                    isSelected={selectedYearId === year.id}
                    onSelect={() => setSelectedYearId(year.id)}
                    onEdit={() => {
                      setEditingYear(year);
                      setYearDialogOpen(true);
                    }}
                    onToggle={() => toggleYear(year.id, !year.is_active).then(() => refetchYears())}
                    onDelete={() => {
                      setDeletingEntity({ type: "year", id: year.id, name: year.name });
                      setDeleteDialogOpen(true);
                    }}
                    showDelete={true}
                  />
                )}
              />
            )}
          </CardContent>
        </Card>

        {/* Blocks Column */}
        <Card className="flex flex-col h-[calc(100vh-12rem)]">
          <ColumnHeader
            title="Blocks"
            description={selectedYear ? selectedYear.name : "Select a year"}
            onAdd={
              selectedYearId
                ? () => {
                    setEditingBlock(null);
                    setBlockDialogOpen(true);
                  }
                : undefined
            }
            addLabel="Add Block"
          />
          <CardContent className="flex-1 overflow-y-auto">
            {!selectedYearId ? (
              <EmptyState
                title="No year selected"
                description="Select a year to view blocks"
              />
            ) : blocksLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : blocksError ? (
              <InlineError message={blocksError.message} onRetry={refetchBlocks} />
            ) : blocks.length === 0 ? (
              <EmptyState
                title="No blocks"
                description="Create the first block for this year"
                actionLabel="Add Block"
                onAction={() => {
                  setEditingBlock(null);
                  setBlockDialogOpen(true);
                }}
              />
            ) : (
              <ReorderableList
                items={blocks}
                onReorder={handleReorderBlocks}
                renderItem={(block) => (
                  <EntityRow
                    id={block.id}
                    title={block.name}
                    subtitle={`${block.code} • Order: ${block.order_no}`}
                    isActive={block.is_active}
                    isSelected={selectedBlockId === block.id}
                    onSelect={() => setSelectedBlockId(block.id)}
                    onEdit={() => {
                      setEditingBlock(block);
                      setBlockDialogOpen(true);
                    }}
                    onToggle={() => toggleBlock(block.id, !block.is_active).then(() => refetchBlocks())}
                    onDelete={() => {
                      setDeletingEntity({ type: "block", id: block.id, name: block.name });
                      setDeleteDialogOpen(true);
                    }}
                    showDelete={true}
                  />
                )}
              />
            )}
          </CardContent>
        </Card>

        {/* Themes Column */}
        <Card className="flex flex-col h-[calc(100vh-12rem)]">
          <ColumnHeader
            title="Themes"
            description={selectedBlock ? selectedBlock.name : "Select a block"}
            onAdd={
              selectedBlockId
                ? () => {
                    setEditingTheme(null);
                    setThemeDialogOpen(true);
                  }
                : undefined
            }
            addLabel="Add Theme"
          />
          <CardContent className="flex-1 overflow-y-auto">
            {!selectedBlockId ? (
              <EmptyState
                title="No block selected"
                description="Select a block to view themes"
              />
            ) : themesLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : themesError ? (
              <InlineError message={themesError.message} onRetry={refetchThemes} />
            ) : themes.length === 0 ? (
              <EmptyState
                title="No themes"
                description="Create the first theme for this block"
                actionLabel="Add Theme"
                onAction={() => {
                  setEditingTheme(null);
                  setThemeDialogOpen(true);
                }}
              />
            ) : (
              <ReorderableList
                items={themes}
                onReorder={handleReorderThemes}
                renderItem={(theme) => (
                  <EntityRow
                    id={theme.id}
                    title={theme.title}
                    subtitle={theme.description || `Order: ${theme.order_no}`}
                    isActive={theme.is_active}
                    onEdit={() => {
                      setEditingTheme(theme);
                      setThemeDialogOpen(true);
                    }}
                    onToggle={() => toggleTheme(theme.id, !theme.is_active).then(() => refetchThemes())}
                    onDelete={() => {
                      setDeletingEntity({ type: "theme", id: theme.id, name: theme.title });
                      setDeleteDialogOpen(true);
                    }}
                    showDelete={true}
                  />
                )}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Mobile: Tabs layout */}
      <div className="md:hidden">
        <Tabs defaultValue="years" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="years">Years</TabsTrigger>
            <TabsTrigger value="blocks">Blocks</TabsTrigger>
            <TabsTrigger value="themes">Themes</TabsTrigger>
          </TabsList>

          <TabsContent value="years">
            <Card>
              <ColumnHeader
                title="Years"
                description="Academic years"
                onAdd={() => {
                  setEditingYear(null);
                  setYearDialogOpen(true);
                }}
                addLabel="Add Year"
              />
              <CardContent>
                {yearsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                    ))}
                  </div>
                ) : yearsError ? (
                  <InlineError message={yearsError.message} onRetry={refetchYears} />
                ) : years.length === 0 ? (
                  <EmptyState
                    title="No years"
                    description="Create your first academic year"
                    actionLabel="Add Year"
                    onAction={() => {
                      setEditingYear(null);
                      setYearDialogOpen(true);
                    }}
                  />
                ) : (
                  <div className="space-y-2">
                    {years.map((year) => (
                      <EntityRow
                        key={year.id}
                        id={year.id}
                        title={year.name}
                        subtitle={`Order: ${year.order_no}`}
                        isActive={year.is_active}
                        isSelected={selectedYearId === year.id}
                        onSelect={() => setSelectedYearId(year.id)}
                        onEdit={() => {
                          setEditingYear(year);
                          setYearDialogOpen(true);
                        }}
                        onToggle={() => toggleYear(year.id, !year.is_active).then(() => refetchYears())}
                        onDelete={() => {
                          setDeletingEntity({ type: "year", id: year.id, name: year.name });
                          setDeleteDialogOpen(true);
                        }}
                        showDelete={true}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="blocks">
            <Card>
              <ColumnHeader
                title="Blocks"
                description={selectedYear ? selectedYear.name : "Select a year"}
                onAdd={
                  selectedYearId
                    ? () => {
                        setEditingBlock(null);
                        setBlockDialogOpen(true);
                      }
                    : undefined
                }
                addLabel="Add Block"
              />
              <CardContent>
                {!selectedYearId ? (
                  <EmptyState
                    title="No year selected"
                    description="Select a year in the Years tab"
                  />
                ) : blocksLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                    ))}
                  </div>
                ) : blocksError ? (
                  <InlineError message={blocksError.message} onRetry={refetchBlocks} />
                ) : blocks.length === 0 ? (
                  <EmptyState
                    title="No blocks"
                    description="Create the first block for this year"
                    actionLabel="Add Block"
                    onAction={() => {
                      setEditingBlock(null);
                      setBlockDialogOpen(true);
                    }}
                  />
                ) : (
                  <div className="space-y-2">
                    {blocks.map((block) => (
                      <EntityRow
                        key={block.id}
                        id={block.id}
                        title={block.name}
                        subtitle={`${block.code} • Order: ${block.order_no}`}
                        isActive={block.is_active}
                        isSelected={selectedBlockId === block.id}
                        onSelect={() => setSelectedBlockId(block.id)}
                        onEdit={() => {
                          setEditingBlock(block);
                          setBlockDialogOpen(true);
                        }}
                        onToggle={() => toggleBlock(block.id, !block.is_active).then(() => refetchBlocks())}
                        onDelete={() => {
                          setDeletingEntity({ type: "block", id: block.id, name: block.name });
                          setDeleteDialogOpen(true);
                        }}
                        showDelete={true}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="themes">
            <Card>
              <ColumnHeader
                title="Themes"
                description={selectedBlock ? selectedBlock.name : "Select a block"}
                onAdd={
                  selectedBlockId
                    ? () => {
                        setEditingTheme(null);
                        setThemeDialogOpen(true);
                      }
                    : undefined
                }
                addLabel="Add Theme"
              />
              <CardContent>
                {!selectedBlockId ? (
                  <EmptyState
                    title="No block selected"
                    description="Select a block in the Blocks tab"
                  />
                ) : themesLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                    ))}
                  </div>
                ) : themesError ? (
                  <InlineError message={themesError.message} onRetry={refetchThemes} />
                ) : themes.length === 0 ? (
                  <EmptyState
                    title="No themes"
                    description="Create the first theme for this block"
                    actionLabel="Add Theme"
                    onAction={() => {
                      setEditingTheme(null);
                      setThemeDialogOpen(true);
                    }}
                  />
                ) : (
                  <div className="space-y-2">
                    {themes.map((theme) => (
                      <EntityRow
                        key={theme.id}
                        id={theme.id}
                        title={theme.title}
                        subtitle={theme.description || `Order: ${theme.order_no}`}
                        isActive={theme.is_active}
                        onEdit={() => {
                          setEditingTheme(theme);
                          setThemeDialogOpen(true);
                        }}
                        onToggle={() => toggleTheme(theme.id, !theme.is_active).then(() => refetchThemes())}
                        onDelete={() => {
                          setDeletingEntity({ type: "theme", id: theme.id, name: theme.title });
                          setDeleteDialogOpen(true);
                        }}
                        showDelete={true}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialogs */}
      <EditYearDialog
        open={yearDialogOpen}
        onOpenChange={setYearDialogOpen}
        year={editingYear}
        onSave={editingYear ? handleUpdateYear : handleCreateYear}
        maxOrderNo={years.length > 0 ? Math.max(...years.map((y) => y.order_no)) : 0}
      />

      <EditBlockDialog
        open={blockDialogOpen}
        onOpenChange={setBlockDialogOpen}
        block={editingBlock}
        yearId={selectedYearId || 0}
        onSave={editingBlock ? handleUpdateBlock : handleCreateBlock}
        maxOrderNo={blocks.length > 0 ? Math.max(...blocks.map((b) => b.order_no)) : 0}
      />

      <EditThemeDialog
        open={themeDialogOpen}
        onOpenChange={setThemeDialogOpen}
        theme={editingTheme}
        blockId={selectedBlockId || 0}
        onSave={editingTheme ? handleUpdateTheme : handleCreateTheme}
        maxOrderNo={themes.length > 0 ? Math.max(...themes.map((t) => t.order_no)) : 0}
      />

      {deletingEntity && (
        <ConfirmDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          title={`Delete ${deletingEntity.type}`}
          description={`Are you sure you want to delete "${deletingEntity.name}"? This action cannot be undone.`}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}
