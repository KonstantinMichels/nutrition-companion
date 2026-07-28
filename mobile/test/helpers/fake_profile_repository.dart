import 'package:nutrition_companion/features/profile/profile_repository.dart';

final class FakeProfileRepository implements ProfileRepository {
  FakeProfileRepository({this.bundle});

  final ProfileBundle? bundle;

  @override
  Future<ProfileBundle?> load() async => bundle;

  @override
  Future<void> save(ProfileBundle bundle) async {}
}
