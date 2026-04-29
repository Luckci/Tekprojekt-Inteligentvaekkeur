class Lesson {
  final String subject;
  final String startTime;
  final String? room;

  Lesson({required this.subject, required this.startTime, this.room});

  // This converts the JSON from your Python script into a Dart object
  factory Lesson.fromJson(Map<String, dynamic> json) {
    return Lesson(
      subject: json['subject'],
      startTime: json['start_time'],
      room: json['room'],
    );
  }
}