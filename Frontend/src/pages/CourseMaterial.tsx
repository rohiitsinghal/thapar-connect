import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen, FileText, ArrowLeft } from "lucide-react";

const materialCatalog: Record<string, { title: string; resources: string[] }> = {
  UCS301: {
    title: "Data Structures",
    resources: [
      "Module 1: Arrays, Linked Lists, Stacks and Queues",
      "Module 2: Trees, Heaps and Hashing",
      "Module 3: Graphs and Traversal Algorithms",
      "Module 4: Sorting and Searching Techniques",
    ],
  },
  UCS503: {
    title: "Operating Systems",
    resources: [
      "Module 1: Processes, Threads and Scheduling",
      "Module 2: Synchronization and Deadlocks",
      "Module 3: Memory Management",
      "Module 4: File Systems and I/O",
    ],
  },
  UCS310: {
    title: "Database Management Systems",
    resources: [
      "Module 1: Relational Model and SQL",
      "Module 2: Normalization and Schema Design",
      "Module 3: Transactions and Concurrency Control",
      "Module 4: Query Processing and Optimization",
    ],
  },
};

const CourseMaterial = () => {
  const [searchParams] = useSearchParams();
  const code = (searchParams.get("code") || "").toUpperCase();
  const selected = materialCatalog[code];

  return (
    <div className="min-h-screen bg-background py-10 px-4">
      <div className="container mx-auto max-w-3xl">
        <div className="mb-6">
          <Button asChild variant="outline" size="sm">
            <Link to="/courses">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Courses
            </Link>
          </Button>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-primary" />
              </div>
              <div>
                <CardTitle className="font-display text-2xl">
                  {selected ? `${selected.title} (${code})` : `Course Material (${code || "Unknown"})`}
                </CardTitle>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {selected ? (
              <div className="space-y-3">
                {selected.resources.map((resource) => (
                  <div
                    key={resource}
                    className="flex items-start gap-2 p-3 rounded-md border border-border bg-card"
                  >
                    <FileText className="w-4 h-4 mt-0.5 text-primary" />
                    <span className="text-sm text-foreground">{resource}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Study material is being prepared for this course. Please check with your instructor.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CourseMaterial;
