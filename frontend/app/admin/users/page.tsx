"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { UsersHeader } from "@/components/admin/users/UsersHeader";
import { UsersFilters } from "@/components/admin/users/UsersFilters";
import { UsersTable } from "@/components/admin/users/UsersTable";
import { UsersSkeleton } from "@/components/admin/users/UsersSkeleton";
import { UsersEmpty } from "@/components/admin/users/UsersEmpty";
import { UsersError } from "@/components/admin/users/UsersError";
import { UserFormDialog } from "@/components/admin/users/UserFormDialog";
import { ConfirmActionDialog } from "@/components/admin/users/ConfirmActionDialog";
import { useAdminUsers, useUserMutations, useCurrentUserId } from "@/lib/admin/users/hooks";
import { User, UserCreate, UserUpdate } from "@/lib/admin/users/types";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{
    title: string;
    description: string;
    confirmLabel?: string;
    action: () => Promise<void>;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const currentUserId = useCurrentUserId();
  const {
    users,
    loading,
    error,
    page,
    pageSize,
    total,
    refetch,
    setPage,
    setPageSize,
    setSearch: setSearchFilter,
    setRoleFilter: setRoleFilterState,
    setStatusFilter: setStatusFilterState,
  } = useAdminUsers({
    q: search,
    role: roleFilter,
    status: statusFilter,
  });

  const { createUser, updateUser, enableUser, disableUser, triggerPasswordReset } =
    useUserMutations();

  const handleAddUser = () => {
    setEditingUser(null);
    setUserDialogOpen(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setUserDialogOpen(true);
  };

  const handleSaveUser = async (data: UserCreate | UserUpdate) => {
    if (editingUser) {
      await updateUser(editingUser.id, data as UserUpdate);
    } else {
      await createUser(data as UserCreate);
    }
    await refetch();
  };

  const handleEnableUser = async (user: User) => {
    await enableUser(user.id);
    await refetch();
  };

  const handleDisableUser = async (user: User) => {
    if (user.id === currentUserId) {
      return; // Should be prevented by UI, but guardrail
    }
    await disableUser(user.id);
    await refetch();
  };

  const handlePasswordReset = async (user: User) => {
    await triggerPasswordReset(user.id);
  };

  const showConfirmDialog = (
    title: string,
    description: string,
    confirmLabel: string,
    action: () => Promise<void>
  ) => {
    setConfirmAction({ title, description, confirmLabel, action });
    setConfirmDialogOpen(true);
  };

  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    try {
      await confirmAction.action();
      await refetch();
    } finally {
      setActionLoading(false);
    }
  };

  const handleRoleChange = (user: User, newRole: string) => {
    if (user.role === newRole) return;
    showConfirmDialog(
      "Change User Role",
      `Changing role from ${user.role} to ${newRole} affects access permissions. Continue?`,
      "Change Role",
      async () => {
        await updateUser(user.id, { role: newRole as any });
      }
    );
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <UsersHeader onAddUser={handleAddUser} />

      {/* Filters */}
      <UsersFilters
        search={search}
        role={roleFilter}
        status={statusFilter}
        onSearchChange={(value) => {
          setSearch(value);
          setSearchFilter(value);
        }}
        onRoleChange={(value) => {
          setRoleFilter(value);
          setRoleFilterState(value);
        }}
        onStatusChange={(value) => {
          setStatusFilter(value);
          setStatusFilterState(value);
        }}
      />

      {/* Content */}
      {loading ? (
        <UsersSkeleton />
      ) : error ? (
        <UsersError message={error.message} onRetry={refetch} />
      ) : users.length === 0 ? (
        <UsersEmpty onAddUser={handleAddUser} />
      ) : (
        <>
          <UsersTable
            users={users}
            currentUserId={currentUserId}
            onEdit={handleEditUser}
            onEnable={(user) => showConfirmDialog("Enable User", `Enable user "${user.name}"?`, "Enable", () => handleEnableUser(user))}
            onDisable={(user) =>
              showConfirmDialog(
                "Disable User",
                `This user will lose access immediately. Disable user "${user.name}"?`,
                "Disable",
                () => handleDisableUser(user)
              )
            }
            onPasswordReset={(user) =>
              showConfirmDialog(
                "Send Password Reset",
                `Send password reset link to "${user.email}"?`,
                "Send Reset",
                () => handlePasswordReset(user)
              )
            }
          />

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} users
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <div className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Dialogs */}
      <UserFormDialog
        open={userDialogOpen}
        onOpenChange={setUserDialogOpen}
        user={editingUser}
        onSave={handleSaveUser}
      />

      {confirmAction && (
        <ConfirmActionDialog
          open={confirmDialogOpen}
          onOpenChange={setConfirmDialogOpen}
          title={confirmAction.title}
          description={confirmAction.description}
          confirmLabel={confirmAction.confirmLabel}
          onConfirm={handleConfirmAction}
          loading={actionLoading}
        />
      )}
    </div>
  );
}
