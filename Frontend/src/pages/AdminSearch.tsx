import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, UserRound, Mail, BadgeInfo, ArrowLeft, LogOut, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import Footer from "@/components/Footer";
import { clearUserSession, getUserSession } from "@/lib/auth";
import { findPersonProfile, getPeopleData, PeopleProfile } from "@/lib/peopleData";

const formatFieldLabel = (value: string): string =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());

const AdminSearch = () => {
  const session = useMemo(() => getUserSession(), []);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<PeopleProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Enter a roll number, employee code, or email.");
      setResult(null);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const peopleData = await getPeopleData();
      const matchedProfile = findPersonProfile(peopleData, trimmedQuery);

      if (!matchedProfile) {
        setResult(null);
        setError("No matching student or faculty record was found.");
        return;
      }

      setResult(matchedProfile);
    } catch (searchError) {
      console.error(searchError);
      setError("Unable to search the workbook data right now.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  if (!session || session.role !== "admin") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-muted/40">
        <Card className="w-full max-w-md shadow-card">
          <CardHeader className="text-center space-y-3">
            <CardTitle className="font-display text-3xl">Admin Access Required</CardTitle>
            <p className="text-sm text-muted-foreground">Log in with the admin account to search records.</p>
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

  const detailsEntries = result ? Object.entries(result.details) : [];

  return (
    <div className="min-h-screen flex flex-col bg-background pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16 space-y-8 flex-1">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Admin lookup</p>
            <h1 className="font-display text-4xl font-bold text-foreground">Search Records</h1>
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
          <CardHeader>
            <CardTitle className="font-display text-xl flex items-center gap-2">
              <Search className="h-5 w-5 text-primary" /> Search by Roll No or Employee Code
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
              <div className="space-y-2">
                <Label htmlFor="admin-search">Record ID</Label>
                <Input
                  id="admin-search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Enter roll number, employee code, or email"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void handleSearch();
                    }
                  }}
                />
              </div>
              <Button onClick={handleSearch} disabled={loading} className="md:min-w-40">
                {loading ? "Searching..." : "Search"}
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Use a roll number for students or an employee code / email for faculty records.
            </p>
            {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
          </CardContent>
        </Card>

        {result ? (
          <Card className="shadow-card overflow-hidden">
            <div className="bg-hero-gradient px-6 py-8 text-primary-foreground">
              <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div className="space-y-3">
                  <Badge className="bg-primary-foreground/10 text-primary-foreground border border-primary-foreground/20 w-fit">
                    {result.role === "student" ? "Student" : "Faculty"}
                  </Badge>
                  <div>
                    <h2 className="font-display text-3xl font-bold">{result.displayName}</h2>
                    <p className="text-primary-foreground/75">{result.primaryId}</p>
                  </div>
                </div>

                <div className="grid gap-2 text-sm md:text-right">
                  <p className="flex items-center gap-2 md:justify-end">
                    <UserRound className="h-4 w-4" /> {result.role === "student" ? "Roll No" : "Employee Code"}: {result.primaryId}
                  </p>
                  <p className="flex items-center gap-2 md:justify-end">
                    <Mail className="h-4 w-4" /> {result.email || "Not available"}
                  </p>
                  <p className="flex items-center gap-2 md:justify-end">
                    <BadgeInfo className="h-4 w-4" /> Login aliases: {result.loginAliases.length}
                  </p>
                </div>
              </div>
            </div>

            <CardContent className="p-6 space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-border bg-secondary/40 p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Role</p>
                  <p className="mt-1 font-medium text-foreground">{result.role === "student" ? "Student" : "Faculty"}</p>
                </div>
                <div className="rounded-xl border border-border bg-secondary/40 p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Primary ID</p>
                  <p className="mt-1 font-medium text-foreground">{result.primaryId}</p>
                </div>
                <div className="rounded-xl border border-border bg-secondary/40 p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Aliases</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.loginAliases.map((alias) => (
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
                    <FileText className="h-4 w-4 text-primary" />
                    <h3 className="font-display text-xl font-semibold">Record Details</h3>
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
        ) : null}
      </div>
      <Footer />
    </div>
  );
};

export default AdminSearch;