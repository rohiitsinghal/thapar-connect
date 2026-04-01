import { Link, useLocation, useNavigate } from "react-router-dom";
import { Calendar, LayoutDashboard, BookOpen, DoorOpen, Clock, Users, Menu, X, ChevronDown } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { clearUserSession, getUserSession } from "@/lib/auth";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { label: "Timetable", path: "/timetable", icon: Calendar },
  { label: "Courses", path: "/courses", icon: BookOpen },
  { label: "Rooms", path: "/rooms", icon: DoorOpen },
  { label: "Exam Schedule", path: "/exams", icon: Clock },
  { label: "Student Sections", path: "/sections", icon: Users },
];

const studentVisiblePaths = new Set(["/dashboard", "/timetable", "/courses", "/exams"]);

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isLanding = ["/", "/login", "/welcome"].includes(location.pathname);
  const session = useMemo(() => getUserSession(), [location.pathname]);
  const visibleNavItems = useMemo(() => {
    if (session?.role !== "student") {
      return navItems;
    }

    return navItems.filter((item) => studentVisiblePaths.has(item.path));
  }, [session]);

  const handleLogout = () => {
    clearUserSession();
    setMobileOpen(false);
    navigate("/login");
  };

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all ${isLanding ? "bg-transparent" : "bg-card/95 backdrop-blur-md border-b border-border shadow-card"}`}>
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        <div className="flex items-center gap-2 select-none" aria-label="ThaparTime brand">
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
        </div>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-3">
          <div className="flex items-center gap-1">
            {visibleNavItems.map((item) => (
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

          {session ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="outline" className="gap-1.5">
                  {session.displayName}
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleLogout}>Log out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              asChild
              size="sm"
              className={isLanding ? "bg-primary-foreground text-primary hover:bg-primary-foreground/90" : ""}
            >
              <Link to="/">Login</Link>
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2 md:hidden">
          {session ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="outline" className="gap-1.5">
                  {session.displayName}
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleLogout}>Log out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              asChild
              size="sm"
              className={isLanding ? "bg-primary-foreground text-primary hover:bg-primary-foreground/90" : ""}
            >
              <Link to="/">Login</Link>
            </Button>
          )}

          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className={isLanding ? "text-primary-foreground" : ""}
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X /> : <Menu />}
          </Button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-card border-b border-border shadow-elevated">
          <div className="px-4 py-3 space-y-1">
            {visibleNavItems.map((item) => (
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

            {session ? (
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center justify-center px-3 py-2.5 mt-2 rounded-md text-sm font-medium bg-primary text-primary-foreground"
              >
                Log out
              </button>
            ) : (
              <Link
                to="/"
                onClick={() => setMobileOpen(false)}
                className="flex items-center justify-center px-3 py-2.5 mt-2 rounded-md text-sm font-medium bg-primary text-primary-foreground"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
