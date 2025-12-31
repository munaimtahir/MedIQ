import { LoadingState } from "@/components/status/LoadingState";

export default function AdminLoading() {
  return (
    <LoadingState
      variant="page"
      title="Loading..."
      description="Please wait while we load the admin panel."
    />
  );
}

