import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Footer from "@/components/Footer";
import { clearUserSession, getUserSession, setPasswordForUser, verifyPassword } from "@/lib/auth";
import { findFacultyProfile, findStudentProfile, getPeopleData, PeopleProfile } from "@/lib/peopleData";
import { toast } from "sonner";
import { LockKeyhole, Mail, UserRound, ArrowLeft, LogOut } from "lucide-react";

const formatFieldLabel = (value: string): string =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());

const Profile = () => {
  const session = useMemo(() => getUserSession(), []);
  const [profile, setProfile] = useState<PeopleProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadProfile = async () => {
      if (!session) {
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

  const roleLabel = session?.role === "student" ? "Student" : session?.role === "instructor" ? "Faculty" : "User";
  const identifierLabel = session?.role === "student" ? "Roll No" : "Employee Code";

  const handlePasswordChange = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!session || !profile) {
      return;
    }

    const trimmedCurrentPassword = currentPassword.trim();
    const trimmedNewPassword = newPassword.trim();
    const trimmedConfirmPassword = confirmPassword.trim();

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

    const authRole = session.role === "student" ? "student" : "instructor";
    if (!verifyPassword(authRole, profile.primaryId, trimmedCurrentPassword)) {
      setPageError("Current password is incorrect.");
      return;
    }

    setSaving(true);
    setPageError("");

    try {
      setPasswordForUser(authRole, profile.primaryId, trimmedNewPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Password updated for this browser");
    } catch (error) {
      console.error(error);
      setPageError("Unable to update the password right now.");
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
                      onChange={(event) => setCurrentPassword(event.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-password">New Password</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm-password">Confirm New Password</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                  />
                </div>

                <p className="text-xs text-muted-foreground">
                  After changing the password, use the new value on the next login for this roll number or employee code.
                </p>

                <Button type="submit" className="w-full" disabled={saving}>
                  Save Password
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