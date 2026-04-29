import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:nfc_manager/ndef_record.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'package:nfc_manager/nfc_manager.dart';
import 'package:nfc_manager_ndef/nfc_manager_ndef.dart';

void main() => runApp(const LudusAlarmApp());

class LudusAlarmApp extends StatelessWidget {
  const LudusAlarmApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.blue),
      home: const LoginScrapeScreen(),
    );
  }
}

class LoginScrapeScreen extends StatefulWidget {
  const LoginScrapeScreen({super.key});

  @override
  State<LoginScrapeScreen> createState() => _LoginScrapeScreenState();
}

class _LoginScrapeScreenState extends State<LoginScrapeScreen> {
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  bool _isLoading = false;
  String _statusMessage = "";
  int _wakeUpOffsetMinutes = 30;

  // Ensure this matches your computer's current IPv4
  final String backendUrl = ""; // e.g. "http://

  Future<void> _startScraping() async {
    setState(() {
      _isLoading = true;
      _statusMessage = "Starting browser...";
    });

    try {
      await Future.delayed(const Duration(seconds: 1));
      setState(() => _statusMessage = "Fetching Schedule...");

      final response = await http.post(
        Uri.parse(backendUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "class_name": "2 B",
          "weeks": 1,
          "username": _userController.text,
          "password": _passController.text,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        List events = data['events'];

        if (events.isNotEmpty) {
          var firstLesson = events[0];
          String startTime = firstLesson['start_time'];
          String date = firstLesson['date'];

          // Calculate Alarm Time
          final DateTime? lessonDT = _parseLessonDateTime(date, startTime);
          if (lessonDT == null) {
            _showError("Could not read lesson date/time from the server response.");
            return;
          }
          DateTime alarmDT = lessonDT.subtract(
            Duration(minutes: _wakeUpOffsetMinutes),
          );

          // Format Payload
          String alarmTimeStr =
              "${alarmDT.hour.toString().padLeft(2, '0')}:${alarmDT.minute.toString().padLeft(2, '0')}";
          String nfcPayload = "ALARM:$alarmTimeStr|DATE:$date";

          _showNfcReadyDialog(nfcPayload, alarmTimeStr);
        } else {
          _showError("No lessons found for the selected period.");
        }
      } else {
        _showError("Backend Error: ${response.body}");
      }
    } catch (e) {
      _showError("Connection failed. Is the Python server running?");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Shows a dialog prompting the user to tap the NFC tag
  void _showNfcReadyDialog(String payload, String time) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text("Ready to Sync"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.nfc, size: 50, color: Colors.blue),
            const SizedBox(height: 15),
            Text("Alarm calculated for $time"),
            const SizedBox(height: 10),
            const Text("Please tap your alarm clock now..."),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              NfcManager.instance.stopSession();
              Navigator.pop(ctx);
            },
            child: const Text("Cancel"),
          ),
        ],
      ),
    );
    // Start the actual NFC writing process
    _writeToNfc(payload);
  }

  NdefRecord _createTextRecord(String text, {String languageCode = 'en'}) {
    final List<int> languageCodeBytes = utf8.encode(languageCode);
    final List<int> textBytes = utf8.encode(text);

    // The first byte of a Text Record is the 'status byte'
    // bit 7: 0 = UTF-8, 1 = UTF-16
    // bit 6: Reserved (0)
    // bit 5-0: length of language code
    final int statusByte = languageCodeBytes.length;

    final List<int> payload = [
      statusByte,
      ...languageCodeBytes,
      ...textBytes,
    ];

    return NdefRecord(
      typeNameFormat: TypeNameFormat.wellKnown,
      type: Uint8List.fromList([0x54]), // 'T' for Text record
      identifier: Uint8List(0),
      payload: Uint8List.fromList(payload),
    );
  }

  DateTime? _parseLessonDateTime(String date, String startTime) {
    final isoCandidate = startTime.contains('T') ? startTime : '$date $startTime';
    return DateTime.tryParse(isoCandidate);
  }

  void _writeToNfc(String payload) async {
    final availability = await NfcManager.instance.checkAvailability();
    if (availability != NfcAvailability.enabled) {
      _showError("NFC is not available on this device.");
      return;
    }

    // Start session without strict polling options for better compatibility
    NfcManager.instance.startSession(
      pollingOptions: {
        NfcPollingOption.iso14443,
        NfcPollingOption.iso15693,
        NfcPollingOption.iso18092,
      },
      onDiscovered: (NfcTag tag) async {
        var ndef = Ndef.from(tag);
        if (ndef == null || !ndef.isWritable) {
          NfcManager.instance.stopSession(errorMessageIos: "Tag not writable");
          return;
        }

        final NdefRecord record = _createTextRecord(payload);

        final NdefMessage message = NdefMessage(records: [record]);

        try {
          await ndef.write(message: message);
          await NfcManager.instance.stopSession();

          if (!mounted) {
            return;
          }

          final navigator = Navigator.of(context, rootNavigator: true);
          if (navigator.canPop()) {
            navigator.pop();
          }

          ScaffoldMessenger.maybeOf(context)?.showSnackBar(
            const SnackBar(
              content: Text("NFC Tag Updated Successfully!"),
              backgroundColor: Colors.green,
            ),
          );
        } catch (e) {
          NfcManager.instance.stopSession(errorMessageIos: "Write failed: $e");
        }
      },
    );
  }

  void _showError(String msg) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Oops!"),
        content: Text(msg),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Ludus Alarm Sync"), centerTitle: true),
      body: SafeArea(
        child: Stack(
          children: [
            SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  children: [
                    const SizedBox(height: 20),
                    const Icon(Icons.alarm_add, size: 80, color: Colors.blue),
                    const SizedBox(height: 20),
                    const Text(
                      "Ludus Login",
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 30),
                    TextField(
                      controller: _userController,
                      decoration: const InputDecoration(
                        labelText: "Username",
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.person),
                      ),
                    ),
                    const SizedBox(height: 15),
                    TextField(
                      controller: _passController,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: "Password",
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.lock),
                      ),
                    ),
                    const SizedBox(height: 30),
                    Text(
                      "Wake up $_wakeUpOffsetMinutes minutes before class",
                      style: const TextStyle(fontSize: 16),
                    ),
                    Slider(
                      value: _wakeUpOffsetMinutes.toDouble(),
                      min: 5,
                      max: 120,
                      divisions: 23,
                      label: "$_wakeUpOffsetMinutes min",
                      onChanged: (val) =>
                          setState(() => _wakeUpOffsetMinutes = val.toInt()),
                    ),
                    const SizedBox(height: 30),
                    SizedBox(
                      width: double.infinity,
                      height: 55,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _startScraping,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue,
                          foregroundColor: Colors.white,
                        ),
                        child: const Text(
                          "Fetch & Sync to NFC",
                          style: TextStyle(fontSize: 18),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_isLoading)
              Positioned.fill(
                child: Container(
                  color: Colors.black54,
                  child: Center(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(32.0),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const CircularProgressIndicator(),
                            const SizedBox(height: 20),
                            Text(
                              _statusMessage,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
