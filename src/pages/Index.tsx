import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, Calendar, BookOpen, DoorOpen, Clock, Users, BarChart3, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroCampus from "@/assets/thapar.jpg";
import Footer from "@/components/Footer";

const features = [
  {
    icon: Calendar,
    title: "Course Timetabling",
    description: "Automated scheduling that minimizes conflicts and optimizes room utilization across all departments.",
  },
  {
    icon: Clock,
    title: "Exam Scheduling",
    description: "Conflict-free examination timetables with proper spacing and room allocation for all courses.",
  },
  {
    icon: DoorOpen,
    title: "Room Management",
    description: "Track room availability, capacity, and equipment across all campus buildings in real-time.",
  },
  {
    icon: Users,
    title: "Student Sectioning",
    description: "Intelligent student-to-section assignment balancing preferences with capacity constraints.",
  },
  {
    icon: BookOpen,
    title: "Course Catalog",
    description: "Comprehensive course database with prerequisites, credits, and department-wise classification.",
  },
  {
    icon: BarChart3,
    title: "Analytics & Reports",
    description: "Utilization reports, conflict analysis, and scheduling efficiency metrics at a glance.",
  },
];

const stats = [
  { value: "350+", label: "Courses Managed" },
  { value: "120+", label: "Classrooms" },
  { value: "15,000+", label: "Students Scheduled" },
  { value: "99.2%", label: "Conflict-Free Rate" },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

const Index = () => {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative min-h-[92vh] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0">
          <img src={heroCampus} alt="Thapar University Campus" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-hero-gradient opacity-85" />
        </div>

        <div className="relative z-10 container mx-auto px-4 text-center pt-16">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
          >
            <span className="inline-block px-4 py-1.5 rounded-full bg-accent/20 text-gold-light text-sm font-medium tracking-wide mb-6 border border-accent/30">
              Comprehensive Academic Scheduling System
            </span>
            <h1 className="font-display text-5xl md:text-7xl font-bold text-primary-foreground mb-6 leading-tight">
              ThaparTime
            </h1>
            <p className="text-lg md:text-xl text-primary-foreground/75 max-w-2xl mx-auto mb-10 leading-relaxed font-body">
              University timetabling solution for Thapar Institute of Engineering & Technology. 
              Automated course scheduling, exam planning, and room management — all in one platform.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild size="lg" className="bg-accent hover:bg-gold-light text-accent-foreground font-semibold text-base px-8 h-12 shadow-elevated">
                <Link to="/dashboard">
                  Open Dashboard <ArrowRight className="ml-2 w-4 h-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="border-primary-foreground/30 text-primary-foreground hover:bg-primary-foreground/10 h-12 px-8 text-base">
                <Link to="/timetable">
                  View Timetable
                </Link>
              </Button>
            </div>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10">
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 2 }}
            className="w-6 h-10 rounded-full border-2 border-primary-foreground/30 flex items-start justify-center p-1.5"
          >
            <div className="w-1.5 h-2.5 rounded-full bg-primary-foreground/50" />
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 bg-card border-b border-border">
        <div className="container mx-auto px-4">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-2 md:grid-cols-4 gap-8"
          >
            {stats.map((stat) => (
              <motion.div key={stat.label} variants={itemVariants} className="text-center">
                <div className="font-display text-3xl md:text-4xl font-bold text-primary">{stat.value}</div>
                <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-background">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
              Comprehensive Scheduling Features
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Everything Thapar University needs to manage academic scheduling efficiently.
            </p>
          </motion.div>

          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {features.map((feature) => (
              <motion.div
                key={feature.title}
                variants={itemVariants}
                className="bg-card rounded-xl p-6 shadow-card hover:shadow-elevated transition-shadow border border-border group"
              >
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <feature.icon className="w-6 h-6 text-primary group-hover:text-primary-foreground transition-colors" />
                </div>
                <h3 className="font-display text-lg font-semibold text-foreground mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 bg-secondary/50">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
              How It Works
            </h2>
          </motion.div>

          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto"
          >
            {[
              { step: "01", title: "Input Course Data", desc: "Departments enter courses, instructors, and constraints into the system." },
              { step: "02", title: "Solver Optimization", desc: "Our constraint solver generates optimal timetables minimizing conflicts." },
              { step: "03", title: "Review & Publish", desc: "Administrators review, fine-tune, and publish the final schedule." },
            ].map((item) => (
              <motion.div key={item.step} variants={itemVariants} className="text-center">
                <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground font-display text-xl font-bold flex items-center justify-center mx-auto mb-4">
                  {item.step}
                </div>
                <h3 className="font-display text-lg font-semibold mb-2">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-hero-gradient text-primary-foreground">
        <div className="container mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
              Ready to Transform Scheduling at Thapar?
            </h2>
            <p className="text-primary-foreground/70 max-w-lg mx-auto mb-8">
              Explore the platform and see how intelligent timetabling can save hundreds of hours every semester.
            </p>
            <Button asChild size="lg" className="bg-accent hover:bg-gold-light text-accent-foreground font-semibold h-12 px-8 shadow-elevated">
              <Link to="/dashboard">
                Get Started <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Index;
