import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, DoorOpen, Users, Monitor, Wifi } from "lucide-react";
import Footer from "@/components/Footer";

const roomsData = [
  { name: "LT-101", building: "LT Block", capacity: 200, type: "Lecture Theatre", equipment: ["Projector", "AC", "WiFi", "Mic"], available: true },
  { name: "LT-102", building: "LT Block", capacity: 150, type: "Lecture Theatre", equipment: ["Projector", "AC", "WiFi"], available: true },
  { name: "LT-103", building: "LT Block", capacity: 180, type: "Lecture Theatre", equipment: ["Projector", "AC", "WiFi", "Mic"], available: false },
  { name: "LT-205", building: "LT Block", capacity: 120, type: "Lecture Theatre", equipment: ["Projector", "AC"], available: true },
  { name: "A-201", building: "A Block", capacity: 60, type: "Classroom", equipment: ["Projector", "AC"], available: true },
  { name: "A-302", building: "A Block", capacity: 45, type: "Classroom", equipment: ["Projector"], available: false },
  { name: "D-302", building: "D Block", capacity: 80, type: "Classroom", equipment: ["Projector", "AC", "WiFi"], available: true },
  { name: "Lab-C1", building: "C Block", capacity: 40, type: "Computer Lab", equipment: ["Computers", "AC", "WiFi", "Projector"], available: true },
  { name: "Lab-C2", building: "C Block", capacity: 40, type: "Computer Lab", equipment: ["Computers", "AC", "WiFi", "Projector"], available: false },
  { name: "C-101", building: "C Block", capacity: 50, type: "Classroom", equipment: ["Projector", "AC"], available: true },
  { name: "Tutorial-1", building: "A Block", capacity: 30, type: "Tutorial Room", equipment: ["Whiteboard"], available: true },
  { name: "Seminar Hall", building: "LT Block", capacity: 300, type: "Seminar Hall", equipment: ["Projector", "AC", "WiFi", "Mic", "Stage"], available: true },
];

const Rooms = () => {
  const [search, setSearch] = useState("");
  const filtered = roomsData.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.building.toLowerCase().includes(search.toLowerCase()) ||
      r.type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen pt-20 pb-0">
      <div className="container mx-auto px-4 pb-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-foreground">Room Management</h1>
            <p className="text-muted-foreground mt-1">{roomsData.length} rooms across campus</p>
          </div>
          <div className="relative w-full md:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Search rooms..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((room) => (
            <Card key={room.name} className="shadow-card hover:shadow-elevated transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <DoorOpen className="w-5 h-5 text-primary" />
                  </div>
                  <Badge variant={room.available ? "default" : "secondary"}>
                    {room.available ? "Available" : "Occupied"}
                  </Badge>
                </div>
                <h3 className="font-display font-semibold text-foreground text-lg">{room.name}</h3>
                <p className="text-sm text-muted-foreground">{room.building} • {room.type}</p>
                <div className="flex items-center gap-1 mt-2 text-sm text-muted-foreground">
                  <Users className="w-3.5 h-3.5" /> Capacity: {room.capacity}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {room.equipment.map((eq) => (
                    <span key={eq} className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-[10px] font-medium">
                      {eq}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Rooms;
