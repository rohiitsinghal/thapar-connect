import { Calendar, BookOpen, DoorOpen, Users, Clock, AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import Footer from "@/components/Footer";

const statCards = [
  { icon: BookOpen, label: "Total Courses", value: "352", change: "+12 this semester", color: "text-primary" },
  { icon: DoorOpen, label: "Active Rooms", value: "124", change: "98% utilization", color: "text-accent" },
  { icon: Users, label: "Students Enrolled", value: "15,247", change: "+8.3% YoY", color: "text-crimson-light" },
  { icon: Clock, label: "Exams Scheduled", value: "186", change: "All conflict-free", color: "text-gold" },
];

const recentSchedules = [
  { course: "UCS301 - Data Structures", time: "Mon/Wed 9:00-10:30", room: "LT-101", dept: "CSED", status: "Confirmed" },
  { course: "UMA031 - Linear Algebra", time: "Tue/Thu 11:00-12:30", room: "LT-205", dept: "SOM", status: "Confirmed" },
  { course: "UEE501 - Power Systems", time: "Mon/Wed 14:00-15:30", room: "D-Block 302", dept: "EIED", status: "Pending" },
  { course: "UCS503 - Operating Systems", time: "Tue/Thu 9:00-10:30", room: "LT-103", dept: "CSED", status: "Confirmed" },
  { course: "UME401 - Thermodynamics", time: "Wed/Fri 11:00-12:30", room: "A-Block 201", dept: "MED", status: "Conflict" },
];

const conflicts = [
  { issue: "Room LT-103 double-booked on Thursday 9:00 AM", severity: "High" },
  { issue: "Dr. Sharma has overlapping lectures Mon 2 PM", severity: "Medium" },
  { issue: "UCS601 exceeds room capacity (45 > 40)", severity: "Low" },
];

const Dashboard = () => {
  return (
    <div className="min-h-screen pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16">
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Academic Scheduling Overview — Spring 2026</p>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((stat) => (
            <Card key={stat.label} className="shadow-card hover:shadow-elevated transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <p className="text-2xl font-display font-bold text-foreground mt-1">{stat.value}</p>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" /> {stat.change}
                    </p>
                  </div>
                  <div className={`w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center ${stat.color}`}>
                    <stat.icon className="w-5 h-5" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Schedules */}
          <div className="lg:col-span-2">
            <Card className="shadow-card">
              <CardHeader>
                <CardTitle className="font-display text-lg">Recent Schedules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="text-left py-2 font-medium">Course</th>
                        <th className="text-left py-2 font-medium">Time</th>
                        <th className="text-left py-2 font-medium">Room</th>
                        <th className="text-left py-2 font-medium">Dept</th>
                        <th className="text-left py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentSchedules.map((s, i) => (
                        <tr key={i} className="border-b border-border last:border-0">
                          <td className="py-3 font-medium text-foreground">{s.course}</td>
                          <td className="py-3 text-muted-foreground">{s.time}</td>
                          <td className="py-3 text-muted-foreground">{s.room}</td>
                          <td className="py-3">
                            <span className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium">
                              {s.dept}
                            </span>
                          </td>
                          <td className="py-3">
                            <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                              s.status === "Confirmed" ? "text-green-600" :
                              s.status === "Pending" ? "text-accent" : "text-destructive"
                            }`}>
                              {s.status === "Confirmed" ? <CheckCircle2 className="w-3 h-3" /> :
                               s.status === "Conflict" ? <AlertTriangle className="w-3 h-3" /> :
                               <Clock className="w-3 h-3" />}
                              {s.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Conflicts */}
            <Card className="shadow-card">
              <CardHeader>
                <CardTitle className="font-display text-lg flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent" /> Conflicts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {conflicts.map((c, i) => (
                  <div key={i} className="p-3 rounded-lg bg-secondary text-sm">
                    <p className="text-foreground">{c.issue}</p>
                    <span className={`text-xs font-medium mt-1 inline-block ${
                      c.severity === "High" ? "text-destructive" : c.severity === "Medium" ? "text-accent" : "text-muted-foreground"
                    }`}>
                      {c.severity} Priority
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Utilization */}
            <Card className="shadow-card">
              <CardHeader>
                <CardTitle className="font-display text-lg">Room Utilization</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { building: "LT Block", pct: 94 },
                  { building: "A Block", pct: 87 },
                  { building: "D Block", pct: 72 },
                  { building: "C Block", pct: 65 },
                ].map((b) => (
                  <div key={b.building}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-foreground font-medium">{b.building}</span>
                      <span className="text-muted-foreground">{b.pct}%</span>
                    </div>
                    <Progress value={b.pct} className="h-2" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Dashboard;
