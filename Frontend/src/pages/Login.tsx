import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import heroCampus from "@/assets/thapar.jpg";

const roleOptions = [
  { value: "admin", label: "Admin" },
  { value: "instructor", label: "Instructor" },
  { value: "student", label: "Student" },
] as const;

const Login = () => {
  const [role, setRole] = useState<string>("");
  const navigate = useNavigate();

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

  return (
    <div className="relative min-h-screen pt-24 pb-16 px-4 flex items-center justify-center overflow-hidden">
      <div className="absolute inset-0">
        <img src={heroCampus} alt="Thapar University Campus" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-hero-gradient opacity-85" />
      </div>

      <div className="relative z-10 w-full max-w-md mx-auto">
        <Card className="shadow-elevated border-border bg-card/95 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="font-display text-2xl">Login</CardTitle>
            <CardDescription>
              Choose your portal role from the dropdown below.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="role-select">Role</Label>
              <Select value={role} onValueChange={setRole}>
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
            </div>

            <Button className="w-full" disabled={!role} onClick={() => navigate("/dashboard")}>
              Continue as {role ? roleOptions.find((r) => r.value === role)?.label : "User"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
