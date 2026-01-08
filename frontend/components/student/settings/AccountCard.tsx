"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Lock } from "lucide-react";

interface AccountCardProps {
  name?: string;
  email?: string;
  role?: string;
  createdAt?: string;
  loading?: boolean;
}

export function AccountCard({ name, email, role, createdAt, loading }: AccountCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-10 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account information</CardTitle>
        <CardDescription>Your account details (read-only)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {name && (
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} disabled />
          </div>
        )}
        {email && (
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={email} disabled />
          </div>
        )}
        {role && (
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Input id="role" value={role} disabled />
          </div>
        )}
        {createdAt && (
          <div className="space-y-2">
            <Label htmlFor="createdAt">Account created</Label>
            <Input
              id="createdAt"
              value={new Date(createdAt).toLocaleDateString()}
              disabled
            />
          </div>
        )}
        <div className="pt-2">
          <Button variant="outline" disabled>
            <Lock className="mr-2 h-4 w-4" />
            Change password (Coming soon)
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
