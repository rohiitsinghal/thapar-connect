export type SectionStudent = {
  name: string;
  rollNo: string;
};

export type SectionAssignment = {
  courseCode: string;
  courseName: string;
  sectionName: string;
  time: string;
  students: SectionStudent[];
};

export type InstructorProfile = {
  employeeId: string;
  name: string;
  assignments: SectionAssignment[];
};

export const instructorProfiles: InstructorProfile[] = [
  {
    employeeId: "EMP001",
    name: "Dr. A. Gupta",
    assignments: [
      {
        courseCode: "UCS301",
        courseName: "Data Structures",
        sectionName: "Section A",
        time: "Mon/Wed 9:00-10:30",
        students: [
          { name: "Aarav Malhotra", rollNo: "102201001" },
          { name: "Priya Sharma", rollNo: "102201002" },
          { name: "Rohan Arora", rollNo: "102201003" },
          { name: "Sana Kapoor", rollNo: "102201004" },
          { name: "Kunal Mehta", rollNo: "102201005" },
        ],
      },
      {
        courseCode: "UCS351",
        courseName: "Data Structures Lab",
        sectionName: "Section L1",
        time: "Thu 11:00-1:00",
        students: [
          { name: "Aarav Malhotra", rollNo: "102201001" },
          { name: "Priya Sharma", rollNo: "102201002" },
          { name: "Rohan Arora", rollNo: "102201003" },
          { name: "Sana Kapoor", rollNo: "102201004" },
          { name: "Kunal Mehta", rollNo: "102201005" },
        ],
      },
    ],
  },
  {
    employeeId: "EMP002",
    name: "Dr. P. Kaur",
    assignments: [
      {
        courseCode: "UCS503",
        courseName: "Operating Systems",
        sectionName: "Section A",
        time: "Tue/Thu 10:00-11:30",
        students: [
          { name: "Ananya Verma", rollNo: "102201041" },
          { name: "Ishaan Sethi", rollNo: "102201042" },
          { name: "Maya Nair", rollNo: "102201043" },
          { name: "Harsh Bedi", rollNo: "102201044" },
          { name: "Neha Bhatia", rollNo: "102201045" },
        ],
      },
      {
        courseCode: "UCS553",
        courseName: "Operating Systems Lab",
        sectionName: "Section L2",
        time: "Fri 2:00-4:00",
        students: [
          { name: "Ananya Verma", rollNo: "102201041" },
          { name: "Ishaan Sethi", rollNo: "102201042" },
          { name: "Maya Nair", rollNo: "102201043" },
          { name: "Harsh Bedi", rollNo: "102201044" },
          { name: "Neha Bhatia", rollNo: "102201045" },
        ],
      },
    ],
  },
  {
    employeeId: "EMP003",
    name: "Dr. R. Singh",
    assignments: [
      {
        courseCode: "UCS310",
        courseName: "Database Management Systems",
        sectionName: "Section B",
        time: "Mon/Thu 11:00-12:30",
        students: [
          { name: "Devansh Raj", rollNo: "102201071" },
          { name: "Ira Chawla", rollNo: "102201072" },
          { name: "Kabir Gill", rollNo: "102201073" },
          { name: "Mehak Khanna", rollNo: "102201074" },
          { name: "Parth Oberoi", rollNo: "102201075" },
        ],
      },
    ],
  },
];

export const getInstructorProfile = (employeeId: string): InstructorProfile => {
  const normalizedId = employeeId.trim().toUpperCase();
  const matched = instructorProfiles.find((profile) => profile.employeeId === normalizedId);
  return matched ?? instructorProfiles[0];
};

export const findInstructorProfile = (employeeId: string): InstructorProfile | null => {
  const normalizedId = employeeId.trim().toUpperCase();
  return instructorProfiles.find((profile) => profile.employeeId === normalizedId) ?? null;
};

export const findStudentByRollNo = (rollNo: string): SectionStudent | null => {
  const normalizedRollNo = rollNo.trim().toUpperCase();
  for (const profile of instructorProfiles) {
    for (const assignment of profile.assignments) {
      const matchedStudent = assignment.students.find(
        (student) => student.rollNo.toUpperCase() === normalizedRollNo
      );
      if (matchedStudent) {
        return matchedStudent;
      }
    }
  }

  return null;
};

export const getAllAssignments = (): SectionAssignment[] =>
  instructorProfiles.flatMap((profile) => profile.assignments);
