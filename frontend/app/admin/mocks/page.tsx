"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BlueprintsTab } from "@/components/admin/mocks/BlueprintsTab";
import { RunsTab } from "@/components/admin/mocks/RunsTab";
import { InstancesTab } from "@/components/admin/mocks/InstancesTab";

export default function MocksPage() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState(tabParam || "blueprints");

  useEffect(() => {
    if (tabParam) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Mock Blueprints</h1>
        <p className="text-muted-foreground">Create and manage mock exam blueprints and generated instances</p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="blueprints">Blueprints</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="instances">Instances</TabsTrigger>
        </TabsList>

        <TabsContent value="blueprints">
          <BlueprintsTab />
        </TabsContent>

        <TabsContent value="runs">
          <RunsTab />
        </TabsContent>

        <TabsContent value="instances">
          <InstancesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
