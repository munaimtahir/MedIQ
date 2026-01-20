/**
 * Submit confirmation dialog
 */

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AlertTriangle } from "lucide-react";

interface SubmitConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  answeredCount: number;
  totalQuestions: number;
  markedCount: number;
}

export function SubmitConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  answeredCount,
  totalQuestions,
  markedCount,
}: SubmitConfirmDialogProps) {
  const unansweredCount = totalQuestions - answeredCount;
  const hasUnanswered = unansweredCount > 0;
  const hasMarked = markedCount > 0;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            {(hasUnanswered || hasMarked) && (
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            )}
            Submit Test Session?
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-3 pt-2">
            <p>
              You are about to submit your session. Once submitted, you cannot make any changes.
            </p>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Answered:</span>
                <span className="font-medium">{answeredCount} / {totalQuestions}</span>
              </div>
              {hasUnanswered && (
                <div className="flex justify-between text-amber-600">
                  <span>Unanswered:</span>
                  <span className="font-medium">{unansweredCount}</span>
                </div>
              )}
              {hasMarked && (
                <div className="flex justify-between text-amber-600">
                  <span>Marked for review:</span>
                  <span className="font-medium">{markedCount}</span>
                </div>
              )}
            </div>

            {hasUnanswered && (
              <p className="text-sm text-amber-600">
                Unanswered questions will be marked as incorrect.
              </p>
            )}

            <p className="font-medium">
              Are you sure you want to submit?
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            Submit Session
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
