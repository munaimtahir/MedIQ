"use client";

import { Card } from "@/components/ui/card";
import type { BlockSummary } from "@/lib/types/analytics";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface BlockAccuracyChartProps {
  data: BlockSummary[];
  title?: string;
}

export function BlockAccuracyChart({
  data,
  title = "Performance by Block",
}: BlockAccuracyChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="mb-4 text-lg font-semibold">{title}</h3>
        <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
          No block data available
        </div>
      </Card>
    );
  }

  const chartData = data.map((item) => ({
    name: item.block_name.substring(0, 20),
    accuracy: item.accuracy_pct,
    attempted: item.attempted,
    correct: item.correct,
  }));

  return (
    <Card className="p-6">
      <h3 className="mb-4 text-lg font-semibold">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <XAxis
            dataKey="name"
            stroke="#888888"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#888888"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="rounded-lg border bg-background p-2 shadow-sm">
                    <div className="grid gap-2">
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Block
                        </span>
                        <span className="font-bold text-foreground">
                          {payload[0].payload.name}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Accuracy
                        </span>
                        <span className="font-bold text-foreground">
                          {payload[0].value}%
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Progress
                        </span>
                        <span className="font-bold text-foreground">
                          {payload[0].payload.correct} / {payload[0].payload.attempted}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar
            dataKey="accuracy"
            fill="hsl(var(--primary))"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
