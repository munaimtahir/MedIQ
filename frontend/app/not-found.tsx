import { EmptyState } from "@/components/status/EmptyState";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <EmptyState
      variant="page"
      title="Page not found"
      description="The page you're looking for doesn't exist or has been moved."
      icon={<FileQuestion className="h-12 w-12 text-slate-400" />}
      actionLabel="Back to Home"
      actionHref="/"
    />
  );
}
