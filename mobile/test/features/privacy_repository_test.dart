import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/privacy/privacy_repository.dart';

void main() {
  test(
    'deletes only the share_plus cache below the temporary directory',
    () async {
      final temporaryDirectory = await Directory.systemTemp.createTemp(
        'nutrition-companion-privacy-test-',
      );
      addTearDown(() => temporaryDirectory.delete(recursive: true));

      final shareCache = Directory('${temporaryDirectory.path}/share_plus');
      final unrelatedFile = File('${temporaryDirectory.path}/keep.txt');
      await shareCache.create();
      await File(
        '${shareCache.path}/sensitive-export.json',
      ).writeAsString('{}');
      await unrelatedFile.writeAsString('keep');

      await deleteSharePlusCache(temporaryDirectory);

      expect(await shareCache.exists(), isFalse);
      expect(await unrelatedFile.readAsString(), 'keep');
    },
  );

  test('accepts an already absent share_plus cache', () async {
    final temporaryDirectory = await Directory.systemTemp.createTemp(
      'nutrition-companion-privacy-test-',
    );
    addTearDown(() => temporaryDirectory.delete(recursive: true));

    await expectLater(deleteSharePlusCache(temporaryDirectory), completes);
  });
}
