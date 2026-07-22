import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, LogOut, Pencil, Search, Trash2, Upload, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import Footer from "@/components/Footer";
import { clearUserSession, getUserSession } from "@/lib/auth";
import {
  deleteFaculty,
  deleteStudent,
  fetchFaculty,
  fetchStudents,
  updateFaculty,
  updateStudent,
  uploadFacultyFile,
  uploadStudentsFile,
  type FacultyRecord,
  type PeopleAdminRole,
  type StudentRecord,
} from "@/lib/peopleAdminApi";

const STUDENT_COLUMNS: Array<{ key: keyof StudentRecord; label: string }> = [
  { key: "roll_no", label: "Roll No" },
  { key: "name", label: "Name" },
  { key: "email", label: "Email" },
  { key: "major", label: "Major" },
  { key: "minor", label: "Minor" },
];

const FACULTY_COLUMNS: Array<{ key: keyof FacultyRecord; label: string }> = [
  { key: "employee_code", label: "Employee Code" },
  { key: "name", label: "Name" },
  { key: "teacher_code", label: "Teacher Code" },
  { key: "designation", label: "Designation" },
  { key: "email", label: "Email" },
];

const STUDENT_EDITABLE_FIELDS = ["name", "email", "major", "minor"] as const;
const FACULTY_EDITABLE_FIELDS = ["name", "teacher_code", "designation", "email"] as const;

const AdminPeople = () => {
  const session = useMemo(() => getUserSession(), []);
  const token = session?.token ?? "";

  const [role, setRole] = useState<PeopleAdminRole>("students");
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [faculty, setFaculty] = useState<FacultyRecord[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploading, setUploading] = useState(false);

  const [editingStudent, setEditingStudent] = useState<StudentRecord | null>(null);
  const [editingFaculty, setEditingFaculty] = useState<FacultyRecord | null>(null);
  const [editFields, setEditFields] = useState<Record<string, string>>({});
  const [savingEdit, setSavingEdit] = useState(false);

  const [deletingStudent, setDeletingStudent] = useState<StudentRecord | null>(null);
  const [deletingFaculty, setDeletingFaculty] = useState<FacultyRecord | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      if (role === "students") {
        setStudents(await fetchStudents(token));
      } else {
        setFaculty(await fetchFaculty(token));
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, token]);

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !token) return;

    setUploading(true);
    setUploadStatus("");
    setError("");

    try {
      const result =
        role === "students" ? await uploadStudentsFile(file, token) : await uploadFacultyFile(file, token);
      setUploadStatus(`Imported ${result.written} record(s). Table now has ${result.count} total.`);
      await loadData();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const filteredStudents = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return students;
    return students.filter((student) =>
      Object.values(student).some((value) => String(value ?? "").toLowerCase().includes(trimmed)),
    );
  }, [students, query]);

  const filteredFaculty = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return faculty;
    return faculty.filter((member) =>
      Object.values(member).some((value) => String(value ?? "").toLowerCase().includes(trimmed)),
    );
  }, [faculty, query]);

  const openEditStudent = (student: StudentRecord) => {
    setEditingStudent(student);
    setEditingFaculty(null);
    const fields: Record<string, string> = {};
    STUDENT_EDITABLE_FIELDS.forEach((field) => {
      fields[field] = String(student[field] ?? "");
    });
    setEditFields(fields);
  };

  const openEditFaculty = (member: FacultyRecord) => {
    setEditingFaculty(member);
    setEditingStudent(null);
    const fields: Record<string, string> = {};
    FACULTY_EDITABLE_FIELDS.forEach((field) => {
      fields[field] = String(member[field] ?? "");
    });
    setEditFields(fields);
  };

  const closeEditDialog = () => {
    setEditingStudent(null);
    setEditingFaculty(null);
    setEditFields({});
  };

  const handleSaveEdit = async () => {
    if (!token) return;
    setSavingEdit(true);
    setError("");

    try {
      if (editingStudent) {
        const updated = await updateStudent(editingStudent.roll_no, editFields, token);
        setStudents((prev) => prev.map((item) => (item.roll_no === updated.roll_no ? { ...item, ...updated } : item)));
      } else if (editingFaculty) {
        const updated = await updateFaculty(editingFaculty.employee_code, editFields, token);
        setFaculty((prev) =>
          prev.map((item) => (item.employee_code === updated.employee_code ? { ...item, ...updated } : item)),
        );
      }
      closeEditDialog();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save changes.");
    } finally {
      setSavingEdit(false);
    }
  };

  if (!session || session.role !== "admin") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-muted/40">
        <Card className="w-full max-w-md shadow-card">
          <CardHeader className="text-center space-y-3">
            <CardTitle className="font-display text-3xl">Admin Access Required</CardTitle>
            <p className="text-sm text-muted-foreground">Log in with the admin account to manage records.</p>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button asChild>
              <Link to="/login">Go to Login</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleConfirmDelete = async () => {
    if (!token) return;
    setDeleting(true);
    setError("");

    try {
      if (deletingStudent) {
        await deleteStudent(deletingStudent.roll_no, token);
        setStudents((prev) => prev.filter((item) => item.roll_no !== deletingStudent.roll_no));
      } else if (deletingFaculty) {
        await deleteFaculty(deletingFaculty.employee_code, token);
        setFaculty((prev) => prev.filter((item) => item.employee_code !== deletingFaculty.employee_code));
      }
      setDeletingStudent(null);
      setDeletingFaculty(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Unable to delete record.");
    } finally {
      setDeleting(false);
    }
  };

  const activeEditRecord = editingStudent ?? editingFaculty;
  const activeDeleteRecord = deletingStudent ?? deletingFaculty;
  const activeEditFieldNames = editingStudent ? STUDENT_EDITABLE_FIELDS : FACULTY_EDITABLE_FIELDS;

  return (
    <div className="min-h-screen flex flex-col bg-background pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16 space-y-8 flex-1">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Admin directory</p>
            <h1 className="font-display text-4xl font-bold text-foreground">Manage People</h1>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button variant="outline" asChild>
              <Link to="/dashboard">
                <ArrowLeft className="mr-2 h-4 w-4" /> Dashboard
              </Link>
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                clearUserSession();
                window.location.href = "/login";
              }}
            >
              <LogOut className="mr-2 h-4 w-4" /> Log out
            </Button>
          </div>
        </div>

        <Card className="shadow-card">
          <CardHeader className="space-y-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <CardTitle className="font-display text-xl flex items-center gap-2">
                <Users className="h-5 w-5 text-primary" /> Students & Faculty
              </CardTitle>

              <Tabs value={role} onValueChange={(value) => setRole(value as PeopleAdminRole)}>
                <TabsList>
                  <TabsTrigger value="students">Students</TabsTrigger>
                  <TabsTrigger value="faculty">Faculty</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
              <div className="space-y-2">
                <Label htmlFor="people-search">Search</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="people-search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={role === "students" ? "Search by roll no, name, email..." : "Search by employee code, name, email..."}
                    className="pl-9"
                  />
                </div>
              </div>

              <div className="flex flex-col items-start gap-2 md:items-end">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={handleFileSelected}
                />
                <Button onClick={() => fileInputRef.current?.click()} disabled={uploading} className="md:min-w-48">
                  <Upload className="mr-2 h-4 w-4" />
                  {uploading ? "Uploading..." : `Upload ${role === "students" ? "Student" : "Faculty"} Excel`}
                </Button>
              </div>
            </div>

            {uploadStatus ? <p className="text-sm text-emerald-600">{uploadStatus}</p> : null}
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </CardHeader>

          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground py-8 text-center">Loading records...</p>
            ) : role === "students" ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {STUDENT_COLUMNS.map((column) => (
                        <TableHead key={column.key as string}>{column.label}</TableHead>
                      ))}
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredStudents.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={STUDENT_COLUMNS.length + 1} className="text-center text-muted-foreground py-8">
                          No matching students.
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredStudents.map((student) => (
                        <TableRow key={student.roll_no}>
                          {STUDENT_COLUMNS.map((column) => (
                            <TableCell key={column.key as string}>{String(student[column.key] ?? "")}</TableCell>
                          ))}
                          <TableCell className="text-right space-x-1">
                            <Button variant="ghost" size="sm" onClick={() => openEditStudent(student)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => setDeletingStudent(student)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {FACULTY_COLUMNS.map((column) => (
                        <TableHead key={column.key as string}>{column.label}</TableHead>
                      ))}
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredFaculty.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={FACULTY_COLUMNS.length + 1} className="text-center text-muted-foreground py-8">
                          No matching faculty.
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredFaculty.map((member) => (
                        <TableRow key={member.employee_code}>
                          {FACULTY_COLUMNS.map((column) => (
                            <TableCell key={column.key as string}>{String(member[column.key] ?? "")}</TableCell>
                          ))}
                          <TableCell className="text-right space-x-1">
                            <Button variant="ghost" size="sm" onClick={() => openEditFaculty(member)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => setDeletingFaculty(member)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={activeEditRecord !== null} onOpenChange={(open) => !open && closeEditDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Edit {editingStudent ? `Student ${editingStudent.roll_no}` : editingFaculty ? `Faculty ${editingFaculty.employee_code}` : ""}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {activeEditFieldNames.map((field) => (
              <div key={field} className="space-y-2">
                <Label htmlFor={`edit-${field}`} className="capitalize">
                  {field.replace(/_/g, " ")}
                </Label>
                <Input
                  id={`edit-${field}`}
                  value={editFields[field] ?? ""}
                  onChange={(event) => setEditFields((prev) => ({ ...prev, [field]: event.target.value }))}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeEditDialog} disabled={savingEdit}>
              Cancel
            </Button>
            <Button onClick={handleSaveEdit} disabled={savingEdit}>
              {savingEdit ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={activeDeleteRecord !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingStudent(null);
            setDeletingFaculty(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this record?</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingStudent
                ? `This will permanently remove student ${deletingStudent.roll_no} (${deletingStudent.name}) from the database.`
                : deletingFaculty
                ? `This will permanently remove faculty ${deletingFaculty.employee_code} (${deletingFaculty.name}) from the database.`
                : ""}{" "}
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void handleConfirmDelete();
              }}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Footer />
    </div>
  );
};

export default AdminPeople;
