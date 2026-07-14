import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen, FileText, ArrowLeft, Download, Loader2 } from "lucide-react";
import { getUserSession } from "@/lib/auth";
import { getCourseCatalog, type CourseCatalogItem } from "@/lib/courseData";
import { downloadCourseMaterial, listCourseMaterial, type CourseMaterialItem } from "@/lib/courseMaterialApi";

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const CourseMaterial = () => {
  const [searchParams] = useSearchParams();
  const courseCode = (searchParams.get("code") || "").toUpperCase();
  const session = getUserSession();

  const [course, setCourse] = useState<CourseCatalogItem | null>(null);
  const [materials, setMaterials] = useState<CourseMaterialItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const catalog = await getCourseCatalog();
        const matchedCourse = catalog.find((item) => item.courseCode === courseCode) || null;

        if (!cancelled) {
          setCourse(matchedCourse);
        }

        if (!session?.token) {
          if (!cancelled) {
            setError("You need to be logged in to view study material.");
          }
          return;
        }

        const items = await listCourseMaterial(courseCode, session.token);
        if (!cancelled) {
          setMaterials(items);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load study material.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [courseCode, session?.token]);

  const handleDownload = async (item: CourseMaterialItem) => {
    if (!session?.token) {
      return;
    }

    setDownloadingId(item.material_id);
    setError("");
    try {
      await downloadCourseMaterial(courseCode, item.material_id, item.file_name, session.token);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Download failed.");
    } finally {
      setDownloadingId(null);
    }
  };

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
                  {course ? `${course.title} (${courseCode})` : `Course Material (${courseCode || "Unknown"})`}
                </CardTitle>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading study material...
              </div>
            ) : error ? (
              <p className="text-sm text-destructive">{error}</p>
            ) : materials.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Study material is being prepared for this course. Please check with your instructor.
              </p>
            ) : (
              <div className="space-y-3">
                {materials.map((item) => (
                  <div
                    key={item.material_id}
                    className="flex items-center justify-between gap-2 p-3 rounded-md border border-border bg-card"
                  >
                    <div className="flex items-start gap-2">
                      <FileText className="w-4 h-4 mt-0.5 text-primary" />
                      <div>
                        <p className="text-sm text-foreground">{item.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.uploaded_by_name} · {formatSize(item.size_bytes)} ·{" "}
                          {new Date(item.uploaded_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={downloadingId === item.material_id}
                      onClick={() => void handleDownload(item)}
                    >
                      {downloadingId === item.material_id ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4 mr-2" />
                      )}
                      Download
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CourseMaterial;
