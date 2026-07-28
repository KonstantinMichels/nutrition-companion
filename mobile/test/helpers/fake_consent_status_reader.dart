import 'package:nutrition_companion/features/privacy/privacy_repository.dart';

final class FakeConsentStatusReader implements AssessmentConsentStatusReader {
  const FakeConsentStatusReader(this.active);

  final bool active;

  @override
  Future<bool> hasActiveAssessmentConsent() async => active;
}
