import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import heroCampus from "@/assets/thapar.jpg";
import { setUserSession } from "@/lib/auth";
import { findInstructorProfile, findStudentByRollNo } from "@/lib/instructorData";

const roleOptions = [
  { value: "admin", label: "Admin" },
  { value: "instructor", label: "Instructor" },
  { value: "student", label: "Student" },
] as const;

const roleFieldConfig = {
  admin: {
    idLabel: "Admin Gmail",
    idPlaceholder: "admin@thapar.edu",
    idType: "email",
    passwordLabel: "Password",
  },
  instructor: {
    idLabel: "Employee ID",
    idPlaceholder: "Enter your employee ID",
    idType: "text",
    passwordLabel: "Password",
  },
  student: {
    idLabel: "Roll No",
    idPlaceholder: "Enter your roll number",
    idType: "text",
    passwordLabel: "Password",
  },
} as const;

const demoCredentials = {
  student: {
    identifier: "1024170213",
    password: "123456789",
  },
  instructor: {
    identifier: "TIET151",
    password: "123456789",
  },
} as const;

const Login = () => {
  const [role, setRole] = useState<string>("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const navigate = useNavigate();

  const selectedRole = role as keyof typeof roleFieldConfig;
  const fieldConfig = role ? roleFieldConfig[selectedRole] : null;

  const helperText = useMemo(() => {
    if (!role) {
      return "Select a role to continue to the platform.";
    }

    if (role === "admin") {
      return "Admin access selected. You can manage scheduling and publish timetables.";
    }

    if (role === "instructor") {
      return "Instructor access selected. You can view and manage teaching schedules.";
    }

    return "Student access selected. You can view timetable and section details.";
  }, [role]);

  const handleRoleChange = (value: string) => {
    setRole(value);
    setIdentifier("");
    setPassword("");
    setLoginError("");
  };

  const isFormValid =
    !!role &&
    identifier.trim().length > 0 &&
    password.trim().length > 0 &&
    (role !== "admin" || identifier.includes("@"));

  const handleLogin = () => {
    if (!isFormValid) {
      return;
    }

    const trimmedIdentifier = identifier.trim();
    const trimmedPassword = password.trim();

    if (
      role === "student" &&
      (trimmedIdentifier.toUpperCase() !== demoCredentials.student.identifier ||
        trimmedPassword !== demoCredentials.student.password)
    ) {
      setLoginError("Use demo student credentials: Roll No 1024170213 and password 123456789.");
      return;
    }

    if (
      role === "instructor" &&
      (trimmedIdentifier.toUpperCase() !== demoCredentials.instructor.identifier ||
        trimmedPassword !== demoCredentials.instructor.password)
    ) {
      setLoginError("Use demo instructor credentials: Employee ID TIET151 and password 123456789.");
      return;
    }

    setLoginError("");
    const displayName =
      role === "student"
        ? findStudentByRollNo(trimmedIdentifier)?.name || `Student ${trimmedIdentifier}`
        : role === "instructor"
        ? findInstructorProfile(trimmedIdentifier)?.name || `Instructor ${trimmedIdentifier}`
        : "Admin";

    setUserSession({
      role: selectedRole,
      displayName,
      identifier: trimmedIdentifier,
    });

    navigate("/dashboard");
  };

  return (
    <div className="relative min-h-screen py-16 px-4 flex items-center justify-center overflow-hidden">
      <div className="absolute inset-0">
        <img src={heroCampus} alt="Thapar University Campus" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-hero-gradient opacity-85" />
      </div>

      <div className="relative z-10 w-full max-w-md mx-auto">
        <Card className="shadow-elevated border-border bg-card/95 backdrop-blur-sm">
          <CardHeader className="text-center">
            <CardTitle className="font-display text-4xl md:text-5xl">ThaparTime</CardTitle>
          </CardHeader>

          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="role-select">Role</Label>
              <Select value={role} onValueChange={handleRoleChange}>
                <SelectTrigger id="role-select">
                  <SelectValue placeholder="Select Admin, Instructor, or Student" />
                </SelectTrigger>
                <SelectContent>
                  {roleOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">{helperText}</p>
              {role === "student" ? (
                <p className="text-xs text-muted-foreground">Demo: Roll No 1024170213, Password 123456789</p>
              ) : null}
              {role === "instructor" ? (
                <p className="text-xs text-muted-foreground">Demo: Employee ID TIET151, Password 123456789</p>
              ) : null}
            </div>

            {fieldConfig && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="identifier-field">{fieldConfig.idLabel}</Label>
                  <Input
                    id="identifier-field"
                    type={fieldConfig.idType}
                    placeholder={fieldConfig.idPlaceholder}
                    value={identifier}
                    onChange={(event) => setIdentifier(event.target.value)}
                    autoComplete={role === "admin" ? "email" : "username"}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password-field">{fieldConfig.passwordLabel}</Label>
                  <Input
                    id="password-field"
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                  />
                </div>
              </>
            )}

            <Button className="w-full" disabled={!isFormValid} onClick={handleLogin}>
              Login as {role ? roleOptions.find((r) => r.value === role)?.label : "User"}
            </Button>
            {loginError ? <p className="text-sm text-destructive">{loginError}</p> : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
