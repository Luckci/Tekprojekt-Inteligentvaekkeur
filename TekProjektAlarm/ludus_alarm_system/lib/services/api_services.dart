import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/lesson.dart';

class ApiService {
  // Replace with your computer's IP!
  static const String baseUrl = 'http://127.0.0.1:8000'; 

  Future<List<Lesson>> fetchSchedule(String user, String pass) async {
    final response = await http.post(
      Uri.parse('$baseUrl/fetch'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'class_name': '2 B', //
        'weeks': 1,
        'username': user,
        'password': pass,
      }),
    );

    if (response.statusCode == 200) {
      List data = jsonDecode(response.body)['events'];
      return data.map((json) => Lesson.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load schedule');
    }
  }
}