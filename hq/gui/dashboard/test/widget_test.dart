// Tests for the structured recipe view: the variant switcher, the notes
// reflow, and that the body is selectable.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:emily_dashboard/main.dart';

/// A recipe shaped like the real migrated ones: shared ingredients, a shared
/// component, a `- variants: here` marker, and variants that carry their own
/// basis.
final Map<String, dynamic> _recipe = {
  'name': 'test bread',
  'ingredients': [
    {'item': 'salt', 'mass': 10},
  ],
  'components': [
    {
      'name': 'shared preamble',
      'steps': ['always do this'],
    },
    {'variants': 'here'},
    {
      'name': 'shared epilogue',
      'steps': ['and always this'],
    },
  ],
  'variants': [
    {
      'name': 'first way',
      'ingredients': [
        {'item': 'flour', 'mass': 500, 'basis': true},
      ],
      'steps': ['knead it'],
    },
    {
      'name': 'second way',
      'ingredients': [
        {'item': 'flour', 'mass': 250, 'basis': true},
      ],
      'steps': ['do not knead it'],
    },
  ],
};

Future<void> _pumpDialog(WidgetTester tester, Map<String, dynamic> recipe) async {
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(
      body: RecipeDetailDialog(
        title: 'test bread',
        recipe: recipe,
        onEdit: () {},
      ),
    ),
  ));
}

void main() {
  testWidgets('shows one variant at a time and switches between them',
      (tester) async {
    await _pumpDialog(tester, _recipe);

    // Both chips are offered, but only the first variant's body is rendered.
    expect(find.widgetWithText(ChoiceChip, 'first way'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'second way'), findsOneWidget);
    expect(find.text('knead it', findRichText: true), findsOneWidget);
    expect(find.text('do not knead it', findRichText: true), findsNothing);

    await tester.tap(find.widgetWithText(ChoiceChip, 'second way'));
    await tester.pumpAndSettle();

    expect(find.text('knead it', findRichText: true), findsNothing);
    expect(find.text('do not knead it', findRichText: true), findsOneWidget);
  });

  testWidgets('shared parts render either side of the variant marker',
      (tester) async {
    await _pumpDialog(tester, _recipe);

    final body = tester.widget<Column>(find
        .descendant(
            of: find.byType(SingleChildScrollView), matching: find.byType(Column))
        .first);

    int indexOfText(String text) => body.children.indexWhere((w) {
          final found = find.descendant(
              of: find.byWidget(w), matching: find.text(text, findRichText: true));
          return found.evaluate().isNotEmpty;
        });

    // preamble < variant body < epilogue, i.e. the marker placed the variant.
    expect(indexOfText('always do this'), lessThan(indexOfText('knead it')));
    expect(indexOfText('knead it'), lessThan(indexOfText('and always this')));
  });

  testWidgets('keeps the entered amount when switching variants',
      (tester) async {
    await _pumpDialog(tester, _recipe);

    // 750g against the first variant's 500g basis is a 1.5x scale, so the
    // shared 10g of salt becomes 15g.
    await tester.enterText(find.byType(TextField), '750');
    await tester.pumpAndSettle();
    expect(find.textContaining('15g salt', findRichText: true), findsOneWidget);

    // The second variant's basis is 250g, so the same 750g is now 3x.
    await tester.tap(find.widgetWithText(ChoiceChip, 'second way'));
    await tester.pumpAndSettle();
    expect(find.text('750'), findsOneWidget);
    expect(find.textContaining('30g salt', findRichText: true), findsOneWidget);
  });

  testWidgets('unwraps hard-wrapped notes but keeps hand-aligned blocks',
      (tester) async {
    await _pumpDialog(tester, {
      'name': 'noted',
      'notes': 'One dough,\nmany shapes.\n\n'
          '  (A) OPEN   - big holes\n'
          '  (B) EVEN   - small holes\n\n'
          'Back to prose\nover two lines.\n',
    });

    // Prose paragraphs are rejoined into a single line each...
    expect(find.text('One dough, many shapes.'), findsOneWidget);
    expect(find.text('Back to prose over two lines.'), findsOneWidget);
    // ...while the indented key keeps its own line breaks and alignment.
    expect(find.text('(A) OPEN   - big holes\n(B) EVEN   - small holes'),
        findsOneWidget);
  });

  testWidgets('the recipe body is selectable', (tester) async {
    await _pumpDialog(tester, _recipe);
    expect(find.byType(SelectionArea), findsOneWidget);
    expect(
        find.descendant(
            of: find.byType(SelectionArea),
            matching: find.text('knead it', findRichText: true)),
        findsOneWidget);

    // Registering with the enclosing SelectionArea is what actually makes text
    // selectable. A bare RichText doesn't, which once left every step and
    // ingredient unselectable while the bullet beside it selected fine — so
    // check the mechanism, not just that the text is in there somewhere.
    // Icons are drawn as glyphs in a RichText of their own; they aren't text
    // and don't take part in a selection, so leave them out.
    final iconGlyphs = find
        .descendant(of: find.byType(Icon), matching: find.byType(RichText))
        .evaluate()
        .toSet();
    final texts = find
        .descendant(
            of: find.byType(SelectionArea), matching: find.byType(RichText))
        .evaluate()
        .where((e) => !iconGlyphs.contains(e))
        .map((e) => e.widget as RichText);

    expect(texts, isNotEmpty);
    for (final t in texts) {
      expect(t.selectionRegistrar, isNotNull,
          reason: 'unselectable text: "${t.text.toPlainText()}"');
    }
  });
}
