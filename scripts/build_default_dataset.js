const fs = require('fs');
const path = require('path');

const targetDir = path.join(__dirname, '..', 'datasets', 'default_university');
const activeDir = path.join(__dirname, '..', 'datasets', 'active_upload');
if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
if (!fs.existsSync(activeDir)) fs.mkdirSync(activeDir, { recursive: true });

// 1. rooms.csv (NO room_type!)
const rooms = [
  { room_id: 'R101', room_name: 'Lecture Hall 101', capacity: 70, building: 'Block A' },
  { room_id: 'R102', room_name: 'Seminar Room 102', capacity: 50, building: 'Block A' },
  { room_id: 'R103', room_name: 'Classroom 103', capacity: 45, building: 'Block A' },
  { room_id: 'R104', room_name: 'Auditorium 104', capacity: 100, building: 'Block A' },
  { room_id: 'R201', room_name: 'Lecture Hall 201', capacity: 60, building: 'Block B' },
  { room_id: 'R202', room_name: 'Classroom 202', capacity: 40, building: 'Block B' },
  { room_id: 'R203', room_name: 'Lecture Hall 203', capacity: 80, building: 'Block B' },
  { room_id: 'R204', room_name: 'Tutorial Room 204', capacity: 35, building: 'Block B' },
  { room_id: 'R301', room_name: 'Auditorium 301', capacity: 90, building: 'Block C' },
  { room_id: 'R302', room_name: 'Classroom 302', capacity: 55, building: 'Block C' },
  { room_id: 'R401', room_name: 'Grand Hall 401', capacity: 120, building: 'Block D' },
  { room_id: 'R402', room_name: 'Lecture Hall 402', capacity: 65, building: 'Block D' }
];
const roomsCsv = 'room_id,room_name,capacity,building\n' +
  rooms.map(r => `${r.room_id},${r.room_name},${r.capacity},${r.building}`).join('\n');
fs.writeFileSync(path.join(targetDir, 'rooms.csv'), roomsCsv);
fs.writeFileSync(path.join(activeDir, 'rooms.csv'), roomsCsv);

// 2. teachers.csv (Teacher, NOT Instructor)
const teachers = [
  { teacher_id: 'T001', teacher_name: 'Dr. Alan Turing', department: 'Computer Science' },
  { teacher_id: 'T002', teacher_name: 'Dr. Grace Hopper', department: 'Computer Science' },
  { teacher_id: 'T003', teacher_name: 'Dr. Claude Shannon', department: 'Information Technology' },
  { teacher_id: 'T004', teacher_name: 'Dr. Ada Lovelace', department: 'Information Technology' },
  { teacher_id: 'T005', teacher_name: 'Dr. John von Neumann', department: 'Mathematics' },
  { teacher_id: 'T006', teacher_name: 'Dr. Katherine Johnson', department: 'Mathematics' },
  { teacher_id: 'T007', teacher_name: 'Dr. Richard Feynman', department: 'Physics' },
  { teacher_id: 'T008', teacher_name: 'Dr. Marie Curie', department: 'Physics' },
  { teacher_id: 'T009', teacher_name: 'Dr. Nikola Tesla', department: 'Electrical Engineering' },
  { teacher_id: 'T010', teacher_name: 'Dr. Michael Faraday', department: 'Electrical Engineering' },
  { teacher_id: 'T011', teacher_name: 'Dr. Henry Ford', department: 'Mechanical Engineering' },
  { teacher_id: 'T012', teacher_name: 'Dr. James Watt', department: 'Mechanical Engineering' },
  { teacher_id: 'T013', teacher_name: 'Dr. Peter Drucker', department: 'Business Administration' },
  { teacher_id: 'T014', teacher_name: 'Dr. Philip Kotler', department: 'Business Administration' },
  { teacher_id: 'T015', teacher_name: 'Dr. Donald Knuth', department: 'Computer Science' },
  { teacher_id: 'T016', teacher_name: 'Dr. Barbara Liskov', department: 'Information Technology' }
];
const teachersCsv = 'teacher_id,teacher_name,department\n' +
  teachers.map(t => `${t.teacher_id},${t.teacher_name},${t.department}`).join('\n');
fs.writeFileSync(path.join(targetDir, 'teachers.csv'), teachersCsv);
fs.writeFileSync(path.join(activeDir, 'teachers.csv'), teachersCsv);

// 3. time_slots.csv
const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const dayCodes = ['MON', 'TUE', 'WED', 'THU', 'FRI'];
const periods = [
  { start: '09:00', end: '10:00', code: '0900' },
  { start: '10:00', end: '11:00', code: '1000' },
  { start: '11:00', end: '12:00', code: '1100' },
  { start: '12:00', end: '13:00', code: '1200' },
  { start: '13:00', end: '14:00', code: '1300' },
  { start: '14:00', end: '15:00', code: '1400' },
  { start: '15:00', end: '16:00', code: '1500' },
  { start: '16:00', end: '17:00', code: '1600' }
];

const slots = [];
days.forEach((day, di) => {
  periods.forEach(p => {
    slots.push({
      slot_id: `${dayCodes[di]}_${p.code}`,
      day: day,
      start_time: p.start,
      end_time: p.end
    });
  });
});
const slotsCsv = 'slot_id,day,start_time,end_time\n' +
  slots.map(s => `${s.slot_id},${s.day},${s.start_time},${s.end_time}`).join('\n');
fs.writeFileSync(path.join(targetDir, 'time_slots.csv'), slotsCsv);
fs.writeFileSync(path.join(activeDir, 'time_slots.csv'), slotsCsv);

// 4. teacher_availability.csv
const avail = [];
teachers.forEach((t, ti) => {
  slots.forEach((s, si) => {
    // 92% available, 8% deterministic unavailable
    const isAvail = !((ti * 7 + si) % 17 === 0);
    avail.push({ teacher_id: t.teacher_id, slot_id: s.slot_id, available: isAvail ? 'true' : 'false' });
  });
});
const availCsv = 'teacher_id,slot_id,available\n' +
  avail.map(a => `${a.teacher_id},${a.slot_id},${a.available}`).join('\n');
fs.writeFileSync(path.join(targetDir, 'teacher_availability.csv'), availCsv);
fs.writeFileSync(path.join(activeDir, 'teacher_availability.csv'), availCsv);

// 5. classes.csv
const courseTemplates = [
  { code: 'CS101', name: 'Intro to Python Programming', dept: 'Computer Science', count: 60, dur: 60, tid: 'T001' },
  { code: 'CS102', name: 'Data Structures and Algorithms', dept: 'Computer Science', count: 48, dur: 60, tid: 'T002' },
  { code: 'CS103', name: 'Operating Systems Lab', dept: 'Computer Science', count: 40, dur: 120, tid: 'T001' },
  { code: 'CS201', name: 'Artificial Intelligence', dept: 'Computer Science', count: 75, dur: 60, tid: 'T015' },
  { code: 'CS202', name: 'Machine Learning Seminar', dept: 'Computer Science', count: 55, dur: 120, tid: 'T002' },
  { code: 'IT101', name: 'Information Systems Design', dept: 'Information Technology', count: 50, dur: 60, tid: 'T003' },
  { code: 'IT102', name: 'Database Architecture', dept: 'Information Technology', count: 65, dur: 60, tid: 'T004' },
  { code: 'IT103', name: 'Web Engineering Studio', dept: 'Information Technology', count: 45, dur: 120, tid: 'T016' },
  { code: 'IT201', name: 'Cloud Computing Infrastructure', dept: 'Information Technology', count: 58, dur: 60, tid: 'T003' },
  { code: 'IT202', name: 'Cybersecurity Principles', dept: 'Information Technology', count: 42, dur: 60, tid: 'T004' },
  { code: 'MA101', name: 'Calculus and Linear Algebra', dept: 'Mathematics', count: 85, dur: 60, tid: 'T005' },
  { code: 'MA102', name: 'Discrete Mathematics', dept: 'Mathematics', count: 60, dur: 60, tid: 'T006' },
  { code: 'MA201', name: 'Probability and Statistics', dept: 'Mathematics', count: 70, dur: 60, tid: 'T005' },
  { code: 'MA202', name: 'Numerical Analysis Workshop', dept: 'Mathematics', count: 35, dur: 120, tid: 'T006' },
  { code: 'PH101', name: 'Classical Mechanics', dept: 'Physics', count: 80, dur: 60, tid: 'T007' },
  { code: 'PH102', name: 'Electromagnetism & Waves', dept: 'Physics', count: 65, dur: 60, tid: 'T008' },
  { code: 'PH103', name: 'Experimental Physics Lab', dept: 'Physics', count: 38, dur: 120, tid: 'T007' },
  { code: 'PH201', name: 'Quantum Physics Fundamentals', dept: 'Physics', count: 45, dur: 60, tid: 'T008' },
  { code: 'EE101', name: 'Circuit Theory & Analysis', dept: 'Electrical Engineering', count: 70, dur: 60, tid: 'T009' },
  { code: 'EE102', name: 'Digital Electronics Lab', dept: 'Electrical Engineering', count: 40, dur: 120, tid: 'T010' },
  { code: 'EE201', name: 'Signals and Systems', dept: 'Electrical Engineering', count: 52, dur: 60, tid: 'T009' },
  { code: 'EE202', name: 'Power Grid Engineering', dept: 'Electrical Engineering', count: 48, dur: 60, tid: 'T010' },
  { code: 'ME101', name: 'Engineering Thermodynamics', dept: 'Mechanical Engineering', count: 75, dur: 60, tid: 'T011' },
  { code: 'ME102', name: 'Fluid Dynamics', dept: 'Mechanical Engineering', count: 62, dur: 60, tid: 'T012' },
  { code: 'ME103', name: 'CAD Modeling Workshop', dept: 'Mechanical Engineering', count: 42, dur: 120, tid: 'T011' },
  { code: 'ME201', name: 'Robotics and Automation', dept: 'Mechanical Engineering', count: 50, dur: 120, tid: 'T012' },
  { code: 'BA101', name: 'Principles of Management', dept: 'Business Administration', count: 90, dur: 60, tid: 'T013' },
  { code: 'BA102', name: 'Financial Accounting', dept: 'Business Administration', count: 65, dur: 60, tid: 'T014' },
  { code: 'BA201', name: 'Organizational Behavior', dept: 'Business Administration', count: 55, dur: 60, tid: 'T013' },
  { code: 'BA202', name: 'Strategic Marketing Studies', dept: 'Business Administration', count: 48, dur: 120, tid: 'T014' },
  { code: 'CS301', name: 'Cloud Native Microservices', dept: 'Computer Science', count: 50, dur: 60, tid: 'T015' },
  { code: 'IT301', name: 'Network Protocol Engineering', dept: 'Information Technology', count: 45, dur: 60, tid: 'T016' },
  { code: 'MA301', name: 'Applied Linear Systems', dept: 'Mathematics', count: 60, dur: 60, tid: 'T005' },
  { code: 'PH301', name: 'Solid State Physics', dept: 'Physics', count: 40, dur: 60, tid: 'T007' },
  { code: 'EE301', name: 'Embedded Systems Architecture', dept: 'Electrical Engineering', count: 45, dur: 120, tid: 'T009' },
  { code: 'ME301', name: 'Finite Element Analysis', dept: 'Mechanical Engineering', count: 40, dur: 120, tid: 'T011' }
];

const classes = [];
courseTemplates.forEach((ct, i) => {
  const cid = 'C' + String(i + 1).padStart(3, '0');
  classes.push({
    class_id: cid,
    course_code: ct.code,
    course_name: ct.name,
    department: ct.dept,
    student_count: ct.count,
    duration_minutes: ct.dur,
    teacher_id: ct.tid
  });
});

const classesCsv = 'class_id,course_code,course_name,department,student_count,duration_minutes,teacher_id\n' +
  classes.map(c => `${c.class_id},${c.course_code},"${c.course_name}",${c.department},${c.student_count},${c.duration_minutes},${c.teacher_id}`).join('\n');
fs.writeFileSync(path.join(targetDir, 'classes.csv'), classesCsv);
fs.writeFileSync(path.join(activeDir, 'classes.csv'), classesCsv);

// 6. course_requirements.csv (NO required_room_type!)
const requirements = [];
const dayPrefs = [
  'Monday|Wednesday|Friday',
  'Tuesday|Thursday',
  'Monday|Wednesday',
  'Tuesday|Friday',
  'Monday|Tuesday|Thursday'
];

classes.forEach((c, i) => {
  const allowed = dayPrefs[i % dayPrefs.length];
  const prefTime = (i % 2 === 0) ? 'Morning' : 'Afternoon';
  let fixedRoom = '';
  let fixedSlot = '';

  if (i === 2) fixedRoom = 'R104'; // C003 fixed in R104
  if (i === 3) fixedSlot = 'TUE_1300'; // C004 fixed at TUE_1300
  if (i === 10) fixedRoom = 'R401'; // MA101 fixed in R401
  if (i === 26) fixedRoom = 'R401'; // BA101 fixed in R401

  requirements.push({
    class_id: c.class_id,
    allowed_days: allowed,
    preferred_time: prefTime,
    fixed_room_id: fixedRoom,
    fixed_slot_id: fixedSlot
  });
});

const reqCsv = 'class_id,allowed_days,preferred_time,fixed_room_id,fixed_slot_id\n' +
  requirements.map(r => `${r.class_id},${r.allowed_days},${r.preferred_time},${r.fixed_room_id},${r.fixed_slot_id}`).join('\n');
fs.writeFileSync(path.join(targetDir, 'course_requirements.csv'), reqCsv);
fs.writeFileSync(path.join(activeDir, 'course_requirements.csv'), reqCsv);

console.log('Sample university dataset created successfully:');
console.log(`- Rooms: ${rooms.length}`);
console.log(`- Teachers: ${teachers.length}`);
console.log(`- Time Slots: ${slots.length}`);
console.log(`- Availability Records: ${avail.length}`);
console.log(`- Classes: ${classes.length}`);
console.log(`- Course Requirements: ${requirements.length}`);
