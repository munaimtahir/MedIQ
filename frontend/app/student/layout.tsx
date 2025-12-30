import { StudentSidebar } from "@/components/student/Sidebar";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <StudentSidebar />
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
