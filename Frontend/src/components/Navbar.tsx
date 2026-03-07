import { Link, useLocation } from "react-router-dom";
import { Calendar, LayoutDashboard, BookOpen, DoorOpen, Clock, Users, Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { label: "Timetable", path: "/timetable", icon: Calendar },
  { label: "Courses", path: "/courses", icon: BookOpen },
  { label: "Rooms", path: "/rooms", icon: DoorOpen },
  { label: "Exam Schedule", path: "/exams", icon: Clock },
  { label: "Student Sections", path: "/sections", icon: Users },
];

const Navbar = () => {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isLanding = location.pathname === "/";

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all ${isLanding ? "bg-transparent" : "bg-card/95 backdrop-blur-md border-b border-border shadow-card"}`}>
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
            <Calendar className="w-5 h-5 text-primary-foreground" />
          </div>
          <div className="leading-tight">
            <span className={`font-display font-bold text-lg ${isLanding ? "text-primary-foreground" : "text-foreground"}`}>
              ThaparTime
            </span>
            <span className={`block text-[10px] tracking-widest uppercase ${isLanding ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
              Thapar University
            </span>
          </div>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
                location.pathname === item.path
                  ? "bg-primary text-primary-foreground"
                  : isLanding
                  ? "text-primary-foreground/80 hover:text-primary-foreground hover:bg-primary-foreground/10"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          ))}
        </div>

        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className={`md:hidden ${isLanding ? "text-primary-foreground" : ""}`}
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X /> : <Menu />}
        </Button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-card border-b border-border shadow-elevated">
          <div className="px-4 py-3 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
