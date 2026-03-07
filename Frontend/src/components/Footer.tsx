import { Calendar } from "lucide-react";
import { Link } from "react-router-dom";

const Footer = () => (
  <footer className="bg-primary text-primary-foreground">
    <div className="container mx-auto px-4 py-12">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="col-span-1 md:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <Calendar className="w-4 h-4 text-accent-foreground" />
            </div>
            <span className="font-display font-bold text-xl">ThaparTime</span>
          </div>
          <p className="text-primary-foreground/70 max-w-md text-sm leading-relaxed">
            Comprehensive Academic Scheduling System for Thapar Institute of Engineering & Technology.
            Streamlining course timetabling, exam scheduling, and room management.
          </p>
        </div>
        <div>
          <h4 className="font-display font-semibold mb-3">Quick Links</h4>
          <div className="space-y-2 text-sm text-primary-foreground/70">
            <Link to="/dashboard" className="block hover:text-primary-foreground transition-colors">Dashboard</Link>
            <Link to="/timetable" className="block hover:text-primary-foreground transition-colors">Timetable</Link>
            <Link to="/courses" className="block hover:text-primary-foreground transition-colors">Courses</Link>
            <Link to="/rooms" className="block hover:text-primary-foreground transition-colors">Rooms</Link>
          </div>
        </div>
        <div>
          <h4 className="font-display font-semibold mb-3">Contact</h4>
          <div className="space-y-2 text-sm text-primary-foreground/70">
            <p>Thapar Institute of Engineering & Technology</p>
            <p>Patiala, Punjab 147004</p>
            <p>registrar@thapar.edu</p>
          </div>
        </div>
      </div>
      <div className="border-t border-primary-foreground/20 mt-8 pt-6 text-center text-sm text-primary-foreground/50">
        © {new Date().getFullYear()} ThaparTime — Thapar Institute of Engineering & Technology. All rights reserved.
      </div>
    </div>
  </footer>
);

export default Footer;
