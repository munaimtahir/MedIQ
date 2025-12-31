import { LoadingState } from "@/components/status/LoadingState";

export default function StudentLoading() {
  return (
    <LoadingState
      variant="page"
      title="Loading..."
      description="Please wait while we load your dashboard."
    />
  );
}

