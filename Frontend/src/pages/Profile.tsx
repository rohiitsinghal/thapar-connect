import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Footer from "@/components/Footer";
import { clearUserSession, getUserSession } from "@/lib/auth";
import { findFacultyProfile, findStudentProfile, getPeopleData, PeopleProfile } from "@/lib/peopleData";
import { changeAdminPassword } from "@/lib/adminAuthApi";
import { changeFacultyPassword } from "@/lib/facultyAuthApi";
import { changeStudentPassword } from "@/lib/studentAuthApi";
import { toast } from "sonner";
import { LockKeyhole, Mail, UserRound, ArrowLeft, LogOut, CheckCircle2 } from "lucide-react";

const formatFieldLabel = (value: string): string =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());

// Admin has no workbook-backed profile (no Students/Faculty sheet row), so we
// synthesize a minimal one for display purposes instead of leaving `profile`
// as null — a null profile previously made the change-password handler
// silently no-op for admins.
const buildAdminProfile = (identifier: string): PeopleProfile => ({
  role: "faculty",
  primaryId: identifier,
  displayName: "Admin",
  email: identifier,
  sourceSheet: "admin",
  loginAliases: [identifier.toUpperCase()],
  details: {},
});

const Profile = () => {
  const session = useMemo(() => getUserSession(), []);
  const [profile, setProfile] = useState<PeopleProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [passwordUpdated, setPasswordUpdated] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadProfile = async () => {
      if (!session) {
        setLoading(false);
        return;
      }

      // Admin isn't in the workbook data, so skip the fetch entirely.
      if (session.role === "admin") {
        setProfile(buildAdminProfile(session.identifier));
        setLoading(false);
        return;
      }

      try {
        const peopleData = await getPeopleData();
        const resolvedProfile =
          session.role === "student"
            ? findStudentProfile(peopleData, session.identifier)
            : session.role === "instructor"
            ? findFacultyProfile(peopleData, session.identifier)
            : null;

        if (!cancelled) {
          setProfile(resolvedProfile);
        }
      } catch (error) {
        console.error(error);
        if (!cancelled) {
          setPageError("Unable to load the profile data right now.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadProfile();

    return () => {
      cancelled = true;
    };
  }, [session]);

  const roleLabel =
    session?.role === "student"
      ? "Student"
      : session?.role === "instructor"
      ? "Faculty"
      : session?.role === "admin"
      ? "Admin"
      : "User";

  const identifierLabel =
    session?.role === "student" ? "Roll No" : session?.role === "admin" ? "Admin Email" : "Employee Code";

  const handlePasswordChange = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Admin has no workbook profile, so don't gate on `profile` for that role.
    if (!session || (!profile && session.role !== "admin")) {
      return;
    }

    const trimmedCurrentPassword = currentPassword.trim();
    const trimmedNewPassword = newPassword.trim();
    const trimmedConfirmPassword = confirmPassword.trim();

    setPasswordUpdated(false);

    if (!trimmedCurrentPassword || !trimmedNewPassword || !trimmedConfirmPassword) {
      setPageError("Fill in all password fields before saving.");
      return;
    }

    if (trimmedNewPassword !== trimmedConfirmPassword) {
      setPageError("New password and confirmation do not match.");
      return;
    }

    if (trimmedNewPassword.length < 5) {
      setPageError("Password should be at least 5 characters long.");
      return;
    }

    setSaving(true);
    setPageError("");

    try {
      if (!session.token) {
        setPageError("Your session has expired. Please log in again.");
        return;
      }

      if (session.role === "student") {
        await changeStudentPassword(session.token, trimmedCurrentPassword, trimmedNewPassword);
      } else if (session.role === "admin") {
        await changeAdminPassword(session.token, trimmedCurrentPassword, trimmedNewPassword);
      } else {
        await changeFacultyPassword(session.token, trimmedCurrentPassword, trimmedNewPassword);
      }

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordUpdated(true);
      toast.success("Password updated");
    } catch (error) {
      console.error(error);
      setPageError(error instanceof Error ? error.message : "Unable to update the password right now.");
    } finally {
      setSaving(false);
    }
  };

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-muted/40">
        <Card className="w-full max-w-md shadow-card">
          <CardHeader className="text-center space-y-3">
            <CardTitle className="font-display text-3xl">Profile Locked</CardTitle>
            <p className="text-sm text-muted-foreground">Log in first to view your personal profile.</p>
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-muted/40">
        <Card className="w-full max-w-md shadow-card">
          <CardHeader className="text-center space-y-3">
            <CardTitle className="font-display text-3xl">Loading Profile</CardTitle>
            <p className="text-sm text-muted-foreground">Fetching your workbook record now.</p>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const detailsEntries = profile ? Object.entries(profile.details) : [];

  return (
    <div className="min-h-screen flex flex-col bg-background pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16 space-y-8 flex-1">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Personal record</p>
            <h1 className="font-display text-4xl font-bold text-foreground">Profile</h1>
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

        {pageError ? (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {pageError}
          </div>
        ) : null}

        <Card className="shadow-card overflow-hidden">
          <div className="bg-hero-gradient px-6 py-8 text-primary-foreground">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="space-y-3">
                <Badge className="bg-primary-foreground/10 text-primary-foreground border border-primary-foreground/20 w-fit">
                  {roleLabel}
                </Badge>
                <div>
                  <h2 className="font-display text-3xl font-bold">{session.displayName}</h2>
                  <p className="text-primary-foreground/75">{session.identifier}</p>
                </div>
              </div>

              <div className="grid gap-2 text-sm md:text-right">
                <p className="flex items-center gap-2 md:justify-end">
                  <UserRound className="h-4 w-4" /> {identifierLabel}: {session.identifier}
                </p>
                <p className="flex items-center gap-2 md:justify-end">
                  <Mail className="h-4 w-4" /> {profile?.email || "Not available"}
                </p>
              </div>
            </div>
          </div>

          <CardContent className="p-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-border bg-secondary/40 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Primary ID</p>
                <p className="mt-1 font-medium text-foreground">{profile?.primaryId || session.identifier}</p>
              </div>
              <div className="rounded-xl border border-border bg-secondary/40 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Login aliases</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {profile?.loginAliases.map((alias) => (
                    <Badge key={alias} variant="outline">
                      {alias}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            {detailsEntries.length > 0 ? (
              <div>
                <div className="mb-3 flex items-center gap-2">
                  <UserRound className="h-4 w-4 text-primary" />
                  <h3 className="font-display text-xl font-semibold">Profile Details</h3>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {detailsEntries.map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-border bg-card p-4 shadow-sm">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">{formatFieldLabel(key)}</p>
                      <p className="mt-1 break-words text-sm font-medium text-foreground">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="font-display text-xl">Change Password</CardTitle>
            </CardHeader>
            <CardContent>
              {passwordUpdated ? (
                <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-600">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  Password updated successfully.
                </div>
              ) : null}

              <form className="space-y-4" onSubmit={handlePasswordChange}>
                <div className="space-y-2">
                  <Label htmlFor="current-password">Current Password</Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="current-password"
                      type="password"
                      className="pl-9"
                      value={currentPassword}
                      onChange={(event) => {
                        setCurrentPassword(event.target.value);
                        setPasswordUpdated(false);
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-password">New Password</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(event) => {
                      setNewPassword(event.target.value);
                      setPasswordUpdated(false);
                    }}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm-password">Confirm New Password</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                      setPasswordUpdated(false);
                    }}
                  />
                </div>

                <p className="text-xs text-muted-foreground">
                  After changing the password, use the new value on the next login for this roll number, employee
                  code, or admin email.
                </p>

                <Button type="submit" className="w-full" disabled={saving}>
                  {saving ? "Saving..." : "Save Password"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Profile;