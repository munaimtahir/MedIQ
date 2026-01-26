"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { motion } from "framer-motion";

const blocksByYear = {
  "First Year": ["A", "B", "C", "D", "E", "F"],
  "Second Year": ["A", "B", "C", "D", "E", "F"],
  "Third Year": ["A", "B", "C", "D", "E", "F"],
  "Fourth Year": ["A", "B", "C", "D", "E", "F"],
  "Final Year": ["A", "B", "C", "D", "E", "F"],
};

const blockNames: Record<string, string> = {
  A: "Anatomy",
  B: "Biochemistry",
  C: "Physiology",
  D: "Pathology",
  E: "Pharmacology",
  F: "Microbiology",
};

const container = {
  hidden: { opacity: 1 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const item = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { opacity: 1, scale: 1 },
};

export function BlocksSection() {
  const [selectedYear, setSelectedYear] = useState("First Year");

  return (
    <section id="blocks" className="bg-slate-50 py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-12 text-center">
          <h2 className="mb-4 text-3xl font-bold text-slate-900 sm:text-4xl">
            Organized by your syllabus
          </h2>
          <p className="text-lg text-slate-600">
            Practice questions aligned with MBBS block structure
          </p>
        </div>

        <Tabs value={selectedYear} onValueChange={setSelectedYear} className="w-full">
          <TabsList className="mb-8 grid w-full grid-cols-5 gap-1 rounded-xl bg-primary p-1">
            {Object.keys(blocksByYear).map((year) => (
              <TabsTrigger
                key={year}
                value={year}
                className="rounded-lg bg-transparent px-4 py-2 text-sm font-medium text-white/90 transition-all hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-white/60 data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm"
              >
                {year.split(" ")[0]}
              </TabsTrigger>
            ))}
          </TabsList>

          {Object.entries(blocksByYear).map(([year, blocks]) => (
            <TabsContent key={year} value={year} className="mt-0">
              <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="grid gap-4 md:grid-cols-3 lg:grid-cols-6"
              >
                {blocks.map((block) => (
                  <motion.div key={block} variants={item}>
                    <Card className="h-full cursor-pointer border-slate-200 bg-white transition-all hover:border-primary hover:shadow-md">
                      <CardHeader className="pb-3">
                        <Badge className="w-fit bg-primary text-white">Block {block}</Badge>
                      </CardHeader>
                      <CardContent>
                        <CardTitle className="text-lg">{blockNames[block]}</CardTitle>
                        <CardDescription className="mt-1 text-xs">{year} curriculum</CardDescription>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </motion.div>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </section>
  );
}
