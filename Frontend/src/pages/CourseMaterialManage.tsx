import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, ArrowLeft, FileText } from "lucide-react";
import { getUserSession } from "@/lib/auth";
import { getInstructorProfile } from "@/lib/instructorData";

type MaterialItem = {
  fileName: string;
  uploadedAt: string;
};

const CourseMaterialManage = () => {
  const [searchParams] = useSearchParams();
  const courseCode = (searchParams.get("code") || "").toUpperCase();

  const session = getUserSession();
  const isInstructor = session?.role === "instructor";
  const profile = session && isInstructor ? getInstructorProfile(session.identifier) : null;

  const assignments = useMemo(() => {
    if (!profile) {
      return [];
    }

    return profile.assignments.filter((assignment) => assignment.courseCode === courseCode);
  }, [profile, courseCode]);

  const [selectedSection, setSelectedSection] = useState(assignments[0]?.sectionName || "");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedItems, setUploadedItems] = useState<MaterialItem[]>([]);

  const storageKey = `material_${profile?.employeeId || ""}_${courseCode}_${selectedSection}`;

  const loadSectionMaterials = (sectionName: string) => {
    if (!profile) {
      setUploadedItems([]);
      return;
    }

    const key = `material_${profile.employeeId}_${courseCode}_${sectionName}`;
    const saved = window.localStorage.getItem(key);
    if (!saved) {
      setUploadedItems([]);
      return;
    }

    try {
      setUploadedItems(JSON.parse(saved) as MaterialItem[]);
    } catch {
      setUploadedItems([]);
    }
  };

  const handleSectionChange = (value: string) => {
    setSelectedSection(value);
    setSelectedFile(null);
    loadSectionMaterials(value);
  };

  const handleUpload = () => {
    if (!profile || !selectedSection || !selectedFile) {
      return;
    }

    const updated = [
      {
        fileName: selectedFile.name,
        uploadedAt: new Date().toLocaleString(),
      },
      ...uploadedItems,
    ];

    window.localStorage.setItem(storageKey, JSON.stringify(updated));
    setUploadedItems(updated);
    setSelectedFile(null);
  };

  useEffect(() => {
    if (selectedSection) {
      loadSectionMaterials(selectedSection);
    }
  }, [selectedSection]);

  if (!isInstructor || !profile) {
    return (
      <div className="min-h-screen bg-background py-10 px-4">
        <div className="container mx-auto max-w-2xl">
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Only instructors can upload study material.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

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
            <CardTitle className="font-display text-2xl">Upload Study Material - {courseCode}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {assignments.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                This course is not part of your teaching assignments.
              </p>
            ) : (
              <>
                <div className="space-y-2">
                  <Label>Section</Label>
                  <Select value={selectedSection} onValueChange={handleSectionChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select section" />
                    </SelectTrigger>
                    <SelectContent>
                      {assignments.map((assignment) => (
                        <SelectItem key={assignment.sectionName} value={assignment.sectionName}>
                          {assignment.sectionName}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="study-material-file">Study Material File</Label>
                  <Input
                    id="study-material-file"
                    type="file"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                  />
                </div>

                <Button onClick={handleUpload} disabled={!selectedSection || !selectedFile}>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Material
                </Button>

                <div className="space-y-3">
                  <h3 className="font-semibold text-foreground">Uploaded Files ({selectedSection})</h3>
                  {uploadedItems.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No files uploaded yet for this section.</p>
                  ) : (
                    uploadedItems.map((item, index) => (
                      <div
                        key={`${item.fileName}-${index}`}
                        className="flex items-center justify-between p-3 border border-border rounded-md"
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-primary" />
                          <span className="text-sm text-foreground">{item.fileName}</span>
                        </div>
                        <span className="text-xs text-muted-foreground">{item.uploadedAt}</span>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CourseMaterialManage;
