import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class TodayState {
  final bool loading;
  final String? error;
  final TodayDashboard? dashboard;

  const TodayState({this.loading = false, this.error, this.dashboard});

  TodayState copyWith({bool? loading, String? error, TodayDashboard? dashboard}) =>
      TodayState(
        loading: loading ?? this.loading,
        error: error,
        dashboard: dashboard ?? this.dashboard,
      );
}

class TodayController extends StateNotifier<TodayState> {
  final OwnlyRepository _repo;
  TodayController(this._repo) : super(const TodayState()) {
    refresh();
  }

  Future<void> refresh() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final d = await _repo.today();
      state = TodayState(dashboard: d);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final todayProvider = StateNotifierProvider<TodayController, TodayState>(
  (ref) => TodayController(ref.watch(repositoryProvider)),
);