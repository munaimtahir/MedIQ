/**
 * React hooks for two-person approval system
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import { notify } from "@/lib/notify";

/**
 * Hook to fetch pending approvals
 */
export function usePendingApprovals() {
  return useQuery({
    queryKey: ["admin", "approvals", "pending"],
    queryFn: api.listPendingApprovals,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

/**
 * Hook to request approval
 */
export function useRequestApproval() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.requestApproval,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "approvals"] });
      notify.success("Approval request created. Waiting for second admin approval.");
    },
    onError: (error: Error) => {
      notify.error(error.message || "Failed to request approval");
    },
  });
}

/**
 * Hook to approve a request
 */
export function useApproveRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, data }: { requestId: string; data: api.ApproveRequest }) =>
      api.approveRequest(requestId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "approvals"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "algorithms"] });
      notify.success("Approval granted. Action executed.");
    },
    onError: (error: Error) => {
      notify.error(error.message || "Failed to approve request");
    },
  });
}

/**
 * Hook to reject a request
 */
export function useRejectRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.rejectRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "approvals"] });
      notify.success("Approval request rejected");
    },
    onError: (error: Error) => {
      notify.error(error.message || "Failed to reject request");
    },
  });
}
