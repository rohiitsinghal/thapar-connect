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
import { loginAdmin } from "@/lib/adminAuthApi";
import { loginFaculty } from "@/lib/facultyAuthApi";
import { loginStudent } from "@/lib/studentAuthApi";

const roleOptions = [
  { value: "admin", label: "Admin" },
  { value: "instructor", label: "Faculty" },
  { value: "student", label: "Student" },
] as const;

const roleFieldConfig = {
  admin: {
    idLabel: "Admin Email",
    idPlaceholder: "admin",
    idType: "email",
    passwordLabel: "Password",
  },
  instructor: {
    idLabel: "Employee Code",
    idPlaceholder: "Enter your employee code",
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

const Login = () => {
  const [role, setRole] = useState<string>("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const selectedRole = role as keyof typeof roleFieldConfig;
  const fieldConfig = role ? roleFieldConfig[selectedRole] : null;

  const helperText = useMemo(() => {
    if (!role) {
      return "Select a role to continue to the platform.";
    }
    if (role === "student") {
      return `Student access selected. `;
    }
  }, [role]);

  const handleRoleChange = (value: string) => {
    setRole(value);
    setIdentifier("");
    setPassword("");
    setLoginError("");
  };

  const isFormValid = !!role && identifier.trim().length > 0 && password.trim().length > 0;

  const handleLogin = async () => {
    if (!isFormValid) {
      return;
    }

    const trimmedIdentifier = identifier.trim();
    const trimmedPassword = password.trim();
    setIsSubmitting(true);

    try {
      if (selectedRole === "admin") {
        if (trimmedIdentifier.toLowerCase() !== "admin@thapar.edu" || trimmedPassword !== "qwertyuiop") {
          setLoginError("Use admin@thapar.edu with password qwertyuiop.");
          return;
        }

        try {
          const result = await loginAdmin(trimmedIdentifier, trimmedPassword);
          setLoginError("");
          setUserSession({
            role: "admin",
            displayName: "Admin",
            identifier: trimmedIdentifier,
            token: result.token,
          });
          navigate("/admin");
        } catch (error) {
          setLoginError(error instanceof Error ? error.message : "Login failed. Please try again.");
        }
        return;
      }

      if (selectedRole === "student") {
        try {
          const result = await loginStudent(trimmedIdentifier, trimmedPassword);
          setLoginError("");
          setUserSession({
            role: selectedRole,
            displayName: result.name,
            identifier: result.roll_no,
            token: result.token,
          });
          navigate("/profile");
        } catch (error) {
          setLoginError(error instanceof Error ? error.message : "Login failed. Please try again.");
        }
        return;
      }

      try {
        const result = await loginFaculty(trimmedIdentifier, trimmedPassword);
        setLoginError("");
        setUserSession({
          role: selectedRole,
          displayName: result.name,
          identifier: result.employee_code,
          token: result.token,
        });
        navigate("/profile");
      } catch (error) {
        setLoginError(error instanceof Error ? error.message : "Login failed. Please try again.");
      }
    } catch (error) {
      console.error(error);
      setLoginError("Unable to load login data right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
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
                  <SelectValue placeholder="Select Admin, Faculty, or Student" />
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
              {role === "admin" ? (
                <p className="text-xs text-muted-foreground"></p>
              ) : null}
              {role === "student" ? (
                <p className="text-xs text-muted-foreground">Login with your roll number and the default password 12345, then change it.</p>
              ) : null}
              {role === "instructor" ? (
                <p className="text-xs text-muted-foreground">Login with your employee code and the default password tiet12345, then change it.</p>
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
                    autoComplete={role === "instructor" ? "username" : "username"}
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

            <Button className="w-full" disabled={!isFormValid || isSubmitting} onClick={handleLogin}>
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
