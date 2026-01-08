"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";

interface EditYearDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  year?: { id: number; name: string; order_no: number; is_active: boolean };
  onSave: (data: { name: string; order_no: number; is_active: boolean }) => Promise<void>;
  maxOrderNo?: number;
}

export function EditYearDialog({
  open,
  onOpenChange,
  year,
  onSave,
  maxOrderNo = 0,
}: EditYearDialogProps) {
  const [name, setName] = useState("");
  const [orderNo, setOrderNo] = useState(1);
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (year) {
      setName(year.name);
      setOrderNo(year.order_no);
      setIsActive(year.is_active);
    } else {
      setName("");
      setOrderNo(maxOrderNo + 1);
      setIsActive(true);
    }
    setError(null);
  }, [year, maxOrderNo, open]);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSave({ name: name.trim(), order_no: orderNo, is_active: isActive });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{year ? "Edit Year" : "Create Year"}</DialogTitle>
          <DialogDescription>
            {year ? "Update year details" : "Create a new academic year"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="year-name">Name *</Label>
            <Input
              id="year-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., 1st Year"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="year-order">Order Number</Label>
            <Input
              id="year-order"
              type="number"
              min="1"
              value={orderNo}
              onChange={(e) => setOrderNo(Number(e.target.value))}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="year-active"
              checked={isActive}
              onCheckedChange={setIsActive}
            />
            <Label htmlFor="year-active">Active</Label>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface EditBlockDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  block?: { id: number; code: string; name: string; order_no: number; is_active: boolean };
  yearId: number;
  onSave: (data: { year_id: number; code: string; name: string; order_no: number; is_active: boolean }) => Promise<void>;
  maxOrderNo?: number;
}

export function EditBlockDialog({
  open,
  onOpenChange,
  block,
  yearId,
  onSave,
  maxOrderNo = 0,
}: EditBlockDialogProps) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [orderNo, setOrderNo] = useState(1);
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (block) {
      setCode(block.code);
      setName(block.name);
      setOrderNo(block.order_no);
      setIsActive(block.is_active);
    } else {
      setCode("");
      setName("");
      setOrderNo(maxOrderNo + 1);
      setIsActive(true);
    }
    setError(null);
  }, [block, maxOrderNo, open]);

  const handleSave = async () => {
    if (!code.trim()) {
      setError("Code is required");
      return;
    }
    if (!name.trim()) {
      setError("Name is required");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSave({
        year_id: yearId,
        code: code.trim(),
        name: name.trim(),
        order_no: orderNo,
        is_active: isActive,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{block ? "Edit Block" : "Create Block"}</DialogTitle>
          <DialogDescription>
            {block ? "Update block details" : "Create a new block"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="block-code">Code *</Label>
            <Input
              id="block-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g., A"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="block-name">Name *</Label>
            <Input
              id="block-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Block A"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="block-order">Order Number</Label>
            <Input
              id="block-order"
              type="number"
              min="1"
              value={orderNo}
              onChange={(e) => setOrderNo(Number(e.target.value))}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="block-active"
              checked={isActive}
              onCheckedChange={setIsActive}
            />
            <Label htmlFor="block-active">Active</Label>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface EditThemeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  theme?: { id: number; title: string; description?: string; order_no: number; is_active: boolean };
  blockId: number;
  onSave: (data: { block_id: number; title: string; description?: string; order_no: number; is_active: boolean }) => Promise<void>;
  maxOrderNo?: number;
}

export function EditThemeDialog({
  open,
  onOpenChange,
  theme,
  blockId,
  onSave,
  maxOrderNo = 0,
}: EditThemeDialogProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [orderNo, setOrderNo] = useState(1);
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (theme) {
      setTitle(theme.title);
      setDescription(theme.description || "");
      setOrderNo(theme.order_no);
      setIsActive(theme.is_active);
    } else {
      setTitle("");
      setDescription("");
      setOrderNo(maxOrderNo + 1);
      setIsActive(true);
    }
    setError(null);
  }, [theme, maxOrderNo, open]);

  const handleSave = async () => {
    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSave({
        block_id: blockId,
        title: title.trim(),
        description: description.trim() || undefined,
        order_no: orderNo,
        is_active: isActive,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{theme ? "Edit Theme" : "Create Theme"}</DialogTitle>
          <DialogDescription>
            {theme ? "Update theme details" : "Create a new theme"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="theme-title">Title *</Label>
            <Input
              id="theme-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Introduction to Anatomy"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="theme-description">Description</Label>
            <Textarea
              id="theme-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="theme-order">Order Number</Label>
            <Input
              id="theme-order"
              type="number"
              min="1"
              value={orderNo}
              onChange={(e) => setOrderNo(Number(e.target.value))}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="theme-active"
              checked={isActive}
              onCheckedChange={setIsActive}
            />
            <Label htmlFor="theme-active">Active</Label>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
