abstract final class DateFormatters {
  static String date(DateTime value) {
    final local = value.toLocal();
    return '${_two(local.day)}.${_two(local.month)}.${local.year.toString().padLeft(4, '0')}';
  }

  static String dateTime(DateTime value) {
    final local = value.toLocal();
    return '${date(local)}, ${_two(local.hour)}:${_two(local.minute)}';
  }

  static String _two(int value) => value.toString().padLeft(2, '0');
}
