import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:async';
import 'dart:convert';
import 'dart:math';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {

  // Set the name of the webpage
  static const appTitle = 'Dashboard';

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: appTitle,
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: MyHomePage(title: appTitle),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;
  @override
  _MyHomePageState createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  List<String> recipes = [];
  List<Map<String, dynamic>> recipeIndex = [];
  int _selectedIndex = 0;
  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  List<Widget> _widgetOptions() => <Widget>[
    // Recipes page (grouped/searchable list <-> graph)
    RecipesPage(
      index: recipeIndex,
      fallbackPaths: recipes,
      onOpen: _fetchRecipeDetails,
    ),
    // Relationship counter page
    Scaffold(
      appBar: AppBar(title: const Text('Relationship time')),
      body: Center(
        child: ElevatedButton(
          onPressed: fetchRelationshipTime,
          child: const Text('Get relationship time'),
        ),
      ),
    ),
    // Why is Emily so great page
    Scaffold(
      appBar: AppBar(title: const Text('Why is Emily so great?')),
      body: Center(
        child: ElevatedButton(
          onPressed: fetchWhyEmilyIsGreat,
          child: const Text('Go on then, tell me'),
        ),
      ),
    ),
    // Reviews page
    Scaffold(
      appBar: AppBar(title: const Text('Reviews')),
      body: const Center(
        child: Text('Reviews still under development...', style: optionStyle),
      ),
    ),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  void initState() {
    super.initState();
    fetchRecipes();
    fetchRecipeIndex();
  }

  Future<void> fetchRecipes() async {
    final response = await http.get(Uri.parse('http://192.168.0.247:10498/recipes'), headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      });
    if (response.statusCode == 200) {
      setState(() {
        recipes = List<String>.from(json.decode(utf8.decode(response.bodyBytes)));
      });
    } else {
      throw Exception('Failed to load recipes');
    }
  }

  Future<void> fetchRecipeIndex() async {
    try {
      final response = await http.get(
        Uri.parse('http://192.168.0.247:10498/recipe-index'),
        headers: {'Accept': 'application/json'},
      );
      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(utf8.decode(response.bodyBytes));
        if (!mounted) return;
        setState(() {
          recipeIndex = data.cast<Map<String, dynamic>>();
        });
      }
    } catch (e) {
      // Older backend without the index endpoint: the Recipes page falls back
      // to plain paths from fetchRecipes().
      print('Error fetching recipe index: $e');
    }
  }

  Future<void> _fetchRecipeDetails(String recipeId) async {
    try {
      String denestedRecipeId = recipeId.replaceAll("/", "..");
      final response =
          await http.get(Uri.parse('http://192.168.0.247:10498/recipes/$denestedRecipeId'));

      if (response.statusCode != 200) {
        throw Exception('Failed to load recipe details');
      }

      final Map<String, dynamic> data = json.decode(utf8.decode(response.bodyBytes));
      final recipe = data["recipe"];
      final String raw = (data["raw"] ?? data["recipe"] ?? "").toString();
      final String title = (data["name"] ?? recipeId).toString();

      if (!mounted) return;

      if (recipe is Map<String, dynamic>) {
        // Structured, scalable view
        showDialog(
          context: context,
          builder: (context) => RecipeDetailDialog(
            title: (recipe["name"] ?? title).toString(),
            recipe: recipe,
            onEdit: () {
              Navigator.pop(context);
              _showRecipeEditDialog(recipeId, raw);
            },
          ),
        );
      } else {
        // Fallback: YAML didn't parse into a mapping — show the raw text
        showDialog(
          context: context,
          builder: (context) {
            return AlertDialog(
              title: Text(title),
              content: ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.6,
                ),
                child: SingleChildScrollView(child: Text(raw)),
              ),
              actions: [
                TextButton(
                    onPressed: () {
                      Navigator.pop(context);
                      _showRecipeEditDialog(recipeId, raw);
                    },
                    child: const Text("edit")),
                TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text("close")),
              ],
            );
          },
        );
      }
    } catch (e) {
      print('Error fetching recipe details: $e');
    }
  }

  void _showRecipeEditDialog(String recipeId, String currentContent) {
    showDialog(
      context: context,
      builder: (context) => RecipeEditDialog(
        recipeId: recipeId,
        initialContent: currentContent,
        onSave: (content) => _updateRecipe(recipeId, content),
      ),
    ).then((_) {
      // Re-open the (now updated) structured view after the editor closes.
      if (mounted) _fetchRecipeDetails(recipeId);
    });
  }

  Future<bool> _updateRecipe(String recipeId, String content) async {
    try {
      String denestedRecipeId = recipeId.replaceAll("/", "..");
      final response = await http.put(
        Uri.parse('http://192.168.0.247:10498/recipes/$denestedRecipeId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'content': content}),
      );
      if (response.statusCode != 200) {
        print('Failed to update recipe: ${response.statusCode}');
        return false;
      }
      return true;
    } catch (e) {
      print('Error updating recipe: $e');
      return false;
    }
  }

  Future<void> fetchRelationshipTime() async {
    try {
      final response = await http.get(Uri.parse('http://192.168.0.247:10498/relationship_time'));

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(utf8.decode(response.bodyBytes));
        showDialog(
            context: context,
            builder: (context) {
              return AlertDialog(
                title: const Text("Relationship time"),
                content: Text(data["time"]),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text("close"))
                ],
              );
            });
      } else {
        throw Exception('Failed to load relationship time');
      }
    } catch (e) {
      print('Error fetching relationship time: $e');
    }
  }

  Future<void> fetchWhyEmilyIsGreat() async {
    try {
      final response = await http.get(Uri.parse('http://192.168.0.247:10498/why_emily_is_great'));

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(utf8.decode(response.bodyBytes));
        showDialog(
            context: context,
            builder: (context) {
              return AlertDialog(
                title: const Text("One reason is:"),
                content: Text(data["reason"]),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text("close"))
                ],
              );
            });
      } else {
        throw Exception('Failed to load why Emily is great');
      }
    } catch (e) {
      print('Error fetching why Emily is great: $e');
    }
  }

  void _show2025BirthdayDialog() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Happy Birthday Mama! 🎉',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 24)),
          content: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.7,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image.asset(
                    'birthday-bom-2025.jpg',
                    height: 500,
                    errorBuilder: (context, error, stackTrace) =>
                      const Icon(Icons.cake, size: 100, color: Colors.pink),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Happy birthday mi amor ❤️',
                    style: TextStyle(fontSize: 18),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'You\'ve achieved so much this year, I\'m so proud of you! You have surpassed most commercial food establishments, despite the oven; grown the family considerably (particularly in the sighthound direction); and started on the path of being a veterinary mogul of Wagga; just to name a few!',
                   style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'I love our life together, and planning for and building our future is the most exciting and rewarding project I have ever been a part of. I am perpetually honoured you chose me, because you are the most amazing person I have ever met. You have your shit more together than most people I know, regardless of age, and you always think for yourself; which alone make you a force to be reckoned with. I am not surprised one bit that they see you as a suitable succession plan for the clinic!',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Then there\'s all the other stuff. You\'re beautiful, smart and friendly; you have such a strong natural aptitude for animal handling and psychology; you bring us little sickly new members of the family and nurse them back to health (then harvest their broken parts as museum artefacts); you keep our house running smoothly and so well stocked and organised; the list will go on as long as I keep sitting here...',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'I love you ∞ + 1',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text('kthxbai'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  void _show2025AnniversaryDialog() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Happy Anniversary! 💍'),
          content: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.7,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image.asset(
                    'anniversary-2025.jpg',
                    height: 500,
                    errorBuilder: (context, error, stackTrace) =>
                      const Icon(Icons.cake, size: 100, color: Colors.pink),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Happy 8 years mi amor ❤️',
                    style: TextStyle(fontSize: 18),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "I don't like thinking about my life without you, because I don't like being sad, but for the sake of this card I did, and the simulation was bleak and depressing 😞",
                   style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "You have brought so many incredible things to my life over the years, and it continues to this day. On one end of the spectrum, things as mundane as my organisational and time management skills have improved where they never really had before; while on the other, we have a legit family together and I feel like a real dad. Then there's all my newfound knowledge of medical and animal things which make people think I'm cool and relatable, there's all the culinary lessons you've given me, the support and opportunity to do my silly projects and waste time seasoning my pans, all the random experiments we do together, the free reign over the workshop, the time and space for my excessive coffee routines, the delicious brown onion steak sauce (and all other dishes too he just deserves a shoutout), and of course, Babos",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 15),
                  const Text(
                    "You're my best friend in the world, and my motivation for pretty much everything. Actually that puts a lot on you; really it's that I don't need to work to motivate myself to do stuff when you're around. I want to make and eat good food with you, I want to go out for walks and exercise with you, I want to cuddle up and watch movies with you, and I just want to spend all my time with you; and when you're gone it all just falls away. Honestly that song \"Ain't no sunshine (when she's gone)\" is bang on",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "You're my whole thing, and I can't wait to see where we end up together. Nobody could ever come close to you, I wish I could let you inside my brain and show you because everyone else is dumb bitches I tell you hwat, I can't believe you're real",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "Be mine forever?",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Love you ∞ + 1',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text('okay let\'s wrap this up'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  void _show3kMillenniversaryDialog() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Happy 3000 days'),
          content: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.7,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image.asset(
                    '3k-millenniversary.jpg',
                    height: 500,
                    errorBuilder: (context, error, stackTrace) =>
                      const Icon(Icons.cake, size: 100, color: Colors.pink),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Happy 3000 days mi amor ❤️',
                    style: TextStyle(fontSize: 18),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "I love you so much. Regardless of how busy, stressful, or chaotic life has been, I have never doubted that you are the one I want to spend my life with. You are the most incredible person I have ever met, and I am still in awe of how good you are at everything you do.",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "What we've built together is the envy of many, and I am regularly reminded of how lucky I am to have found someone who supports my dreams and silly ideas so strongly. As cliched as it is, I really think we can do just about anything we set our minds to, and we're only just getting started.",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "For all the times I have not properly shown my love and appreciation for you, I am sorry. I tend to shut down a bit when I get stressed, and I hate that you are usually the one who suffers the consequences. This is the biggest thing I want to improve about myself at the moment, because you, the love we have, and the life we live, deserve to be cherished, always.",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Love you ∞ + 1, silly beautiful clever perfect girl',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text("By closing this dialog I acknowledge that papa loves mama the most"),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  void _show2026BirthdayDialog() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Happy Birthday mi amor!'),
          content: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.7,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image.asset(
                    '2026-bday.jpg',
                    height: 500,
                    errorBuilder: (context, error, stackTrace) =>
                      const Icon(Icons.cake, size: 100, color: Colors.pink),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Happy birthday my love ❤️',
                    style: TextStyle(fontSize: 18),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "I'm so proud of you and your achievements this past year. We really are living the dream, and that's all thanks to you and your hard work.",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "We have so much to learn about our new land and new family members, and I'm so excited to do it together and continue to build our little empire. I'm also excited to cook more delicious food together, it's always my faourite part of the day (even when it fails miserably), and it seems like increasingly much will be grown on our land in the future! Despite the fact that you really carry the team sometimes, I still feel like we make a really great team.",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "I hope this next year brings continued professional and parental growth (more money, more kids), and maybe no more Udon 🤷",
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'I love you ∞ + 1, always',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text("Wow you're right, I am the best and coolest person to ever live"),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  void _show2026AnniversaryDialog() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Happy Anniversary! 💍'),
          content: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.7,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // TODO: replace with anniversary image asset
                  const Icon(Icons.favorite, size: 100, color: Colors.pink),
                  const SizedBox(height: 16),
                  const Text(
                    // TODO: fill in anniversary greeting
                    'Happy Anniversary mi amor ❤️',
                    style: TextStyle(fontSize: 18),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  // TODO: fill in anniversary message paragraphs
                  const SizedBox(height: 16),
                  const Text(
                    'Love you ∞ + 1',
                    style: TextStyle(fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text('kthxbai'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        leading: Builder(
          builder: (context) {
            return IconButton(
              icon: const Icon(Icons.menu),
              onPressed: () {
                Scaffold.of(context).openDrawer();
              },
            );
          },
        ),
      ),
      body: Stack(
        children: [
          _widgetOptions()[_selectedIndex],
          Positioned(
            right: 16,
            bottom: 304,
            child: GestureDetector(
              onTap: _show2025BirthdayDialog,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.pink[100],
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.2),
                      spreadRadius: 1,
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.cake,
                  color: Colors.pink,
                  size: 30,
                ),
              ),
            ),
          ),
          Positioned(
            right: 16,
            bottom: 232,
            child: GestureDetector(
              onTap: _show2025AnniversaryDialog,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.cyan[100],
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.2),
                      spreadRadius: 1,
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.favorite,
                  color: Colors.pink,
                  size: 30,
                ),
              ),
            ),
          ),
          Positioned(
            right: 16,
            bottom: 160,
            child: GestureDetector(
              onTap: _show3kMillenniversaryDialog,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.deepPurple[400],
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.2),
                      spreadRadius: 1,
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.three_k,
                  color: Colors.pink,
                  size: 30,
                ),
              ),
            ),
          ),
          Positioned(
            right: 16,
            bottom: 88,
            child: GestureDetector(
              onTap: _show2026BirthdayDialog,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.pink[300],
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.2),
                      spreadRadius: 1,
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.cake,
                  color: Colors.pink,
                  size: 30,
                ),
              ),
            ),
          ),
          Positioned(
            right: 16,
            bottom: 16,
            child: GestureDetector(
              onTap: _show2026AnniversaryDialog,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.cyan[300],
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.2),
                      spreadRadius: 1,
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.all_inclusive,
                  color: Colors.pink,
                  size: 30,
                ),
              ),
            ),
          ),
        ],
      ),
      drawer: Drawer(
        // Add a ListView to the drawer. This ensures the user can scroll
        // through the options in the drawer if there isn't enough vertical
        // space to fit everything.
        child: ListView(
          // Important: Remove any padding from the ListView.
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(
                color: Colors.blue,
              ),
              child: Text('Drawer Header'),
            ),
            ListTile(
              title: const Text('Recipes'),
              selected: _selectedIndex == 0,
              onTap: () {
                // Update the state of the app
                _onItemTapped(0);

                // Then close the drawer
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: const Text('Relationship counter'),
              selected: _selectedIndex == 1,
              onTap: () {
                // Update the state of the app
                _onItemTapped(1);
                // Then close the drawer
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: const Text('Why is Emily so great?'),
              selected: _selectedIndex == 2,
              onTap: () {
                // Update the state of the app
                _onItemTapped(2);
                // Then close the drawer
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: const Text('Reviews'),
              selected: _selectedIndex == 3,
              onTap: () {
                // Update the state of the app
                _onItemTapped(3);
                // Then close the drawer
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Recipe rendering + scaling
// ---------------------------------------------------------------------------

/// Format a (possibly scaled) numeric amount for display: adaptive precision,
/// trailing zeros stripped. e.g. 0.15, 2.5, 22.5, 1800.
String _fmtNum(num value) {
  final double v = value.toDouble();
  final double abs = v.abs();
  String s;
  if (abs >= 100) {
    s = v.toStringAsFixed(0);
  } else if (abs >= 1) {
    s = v.toStringAsFixed(1);
  } else {
    s = v.toStringAsFixed(2);
  }
  if (s.contains('.')) {
    s = s.replaceAll(RegExp(r'0+$'), '').replaceAll(RegExp(r'\.$'), '');
  }
  return s;
}

/// Find the single ingredient flagged `basis: true`, searching top-level
/// ingredients first, then each component's ingredients.
Map? _findBasis(Map recipe) {
  Map? scan(dynamic list) {
    if (list is List) {
      for (final ing in list) {
        if (ing is Map && ing['basis'] == true) return ing;
      }
    }
    return null;
  }

  final top = scan(recipe['ingredients']);
  if (top != null) return top;
  final comps = recipe['components'];
  if (comps is List) {
    for (final c in comps) {
      if (c is Map) {
        final found = scan(c['ingredients']);
        if (found != null) return found;
      }
    }
  }
  return null;
}

/// The reference amount of the basis ingredient (mass preferred, else qty).
double? _basisReference(Map? basis) {
  if (basis == null) return null;
  if (basis['mass'] is num) return (basis['mass'] as num).toDouble();
  if (basis['qty'] is num) return (basis['qty'] as num).toDouble();
  return null;
}

/// The unit to label the basis input with ('g' for masses, else the qty unit).
String _basisUnit(Map basis) {
  if (basis['mass'] is num) return 'g';
  final u = (basis['unit'] ?? '').toString();
  return u == 'ea' ? '' : u;
}

/// Human-readable, scaled amount string for one ingredient, e.g.
/// "500g", "1 tbsp", "20g (1 tbsp)", "3", "2 parts".
String _ingredientAmount(Map ing, double scale) {
  String? massStr;
  String? qtyStr;
  if (ing['mass'] is num) {
    massStr = '${_fmtNum((ing['mass'] as num) * scale)}g';
  }
  if (ing['qty'] is num) {
    final String q = _fmtNum((ing['qty'] as num) * scale);
    final String unit = (ing['unit'] ?? '').toString();
    if (unit.isEmpty || unit == 'ea') {
      qtyStr = q;
    } else if (unit == 'part') {
      qtyStr = '$q ${q == '1' ? 'part' : 'parts'}';
    } else {
      qtyStr = '$q $unit';
    }
  }
  if (massStr != null && qtyStr != null) return '$massStr ($qtyStr)';
  return massStr ?? qtyStr ?? '';
}

/// A scrollable, structured recipe view with an optional scaling control.
class RecipeDetailDialog extends StatefulWidget {
  const RecipeDetailDialog({
    super.key,
    required this.title,
    required this.recipe,
    required this.onEdit,
  });

  final String title;
  final Map<String, dynamic> recipe;
  final VoidCallback onEdit;

  @override
  State<RecipeDetailDialog> createState() => _RecipeDetailDialogState();
}

class _RecipeDetailDialogState extends State<RecipeDetailDialog> {
  Map? _basis;
  double? _reference;
  late final TextEditingController _basisController;
  double _scale = 1.0;

  @override
  void initState() {
    super.initState();
    _basis = _findBasis(widget.recipe);
    _reference = _basisReference(_basis);
    _basisController = TextEditingController(
      text: _reference != null ? _fmtNum(_reference!) : '',
    );
  }

  @override
  void dispose() {
    _basisController.dispose();
    super.dispose();
  }

  void _onBasisChanged(String text) {
    final entered = double.tryParse(text.trim());
    setState(() {
      if (entered != null && _reference != null && _reference! > 0) {
        _scale = entered / _reference!;
      } else {
        _scale = 1.0;
      }
    });
  }

  void _resetScale() {
    setState(() {
      _scale = 1.0;
      if (_reference != null) _basisController.text = _fmtNum(_reference!);
    });
  }

  @override
  Widget build(BuildContext context) {
    final recipe = widget.recipe;
    final children = <Widget>[];

    final yieldText = recipe['yield']?.toString();
    if (yieldText != null && yieldText.trim().isNotEmpty) {
      children.add(Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(
          yieldText,
          style: const TextStyle(
              fontStyle: FontStyle.italic, color: Colors.black54),
        ),
      ));
    }

    final source = recipe['source']?.toString();
    if (source != null && source.trim().isNotEmpty) {
      children.add(Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: SelectableText(
          'source: $source',
          style: const TextStyle(fontSize: 12, color: Colors.blue),
        ),
      ));
    }

    // Scaling control (only when a basis ingredient exists).
    if (_basis != null && _reference != null) {
      final unit = _basisUnit(_basis!);
      final item = (_basis!['item'] ?? 'basis').toString();
      children.add(Card(
        color: Colors.blue[50],
        elevation: 0,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _basisController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: '$item${unit.isNotEmpty ? ' ($unit)' : ''}',
                    isDense: true,
                    border: const OutlineInputBorder(),
                  ),
                  onChanged: _onBasisChanged,
                ),
              ),
              const SizedBox(width: 12),
              Text('×${_fmtNum(_scale)}',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              IconButton(
                icon: const Icon(Icons.refresh, size: 20),
                tooltip: 'reset to original',
                onPressed: _resetScale,
              ),
            ],
          ),
        ),
      ));
      children.add(const SizedBox(height: 4));
    }

    // Top-level ingredients.
    final ingredients = recipe['ingredients'];
    if (ingredients is List && ingredients.isNotEmpty) {
      children.add(_sectionHeader('Ingredients'));
      children.addAll(ingredients.map((ing) => _ingredientWidget(ing)));
      children.add(const SizedBox(height: 8));
    }

    // Top-level steps.
    final steps = recipe['steps'];
    if (steps is List && steps.isNotEmpty) {
      children.add(_sectionHeader('Steps'));
      children.addAll(_stepWidgets(steps));
      children.add(const SizedBox(height: 8));
    }

    // Components.
    final components = recipe['components'];
    if (components is List) {
      for (final comp in components) {
        if (comp is! Map) continue;
        children.add(const Divider());
        final cname = (comp['name'] ?? '').toString();
        if (cname.isNotEmpty) {
          children.add(Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text(
              cname,
              style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Colors.indigo),
            ),
          ));
        }
        final cyield = comp['yield']?.toString();
        if (cyield != null && cyield.trim().isNotEmpty) {
          children.add(Text(
            cyield,
            style: const TextStyle(
                fontStyle: FontStyle.italic, color: Colors.black54),
          ));
        }
        final cIng = comp['ingredients'];
        final hasCIng = cIng is List && cIng.isNotEmpty;
        if (hasCIng) {
          children.addAll(cIng.map((ing) => _ingredientWidget(ing)));
        }
        final cSteps = comp['steps'];
        if (cSteps is List && cSteps.isNotEmpty) {
          if (hasCIng) children.add(const SizedBox(height: 4));
          children.addAll(_stepWidgets(cSteps));
        }
        final cNotes = comp['notes']?.toString();
        if (cNotes != null && cNotes.trim().isNotEmpty) {
          children.add(_notesWidget(cNotes));
        }
      }
    }

    // Top-level notes.
    final notes = recipe['notes']?.toString();
    if (notes != null && notes.trim().isNotEmpty) {
      children.add(const Divider());
      children.add(_sectionHeader('Notes'));
      children.add(_notesWidget(notes));
    }

    if (children.isEmpty) {
      children.add(const Text('(empty recipe)'));
    }

    return AlertDialog(
      title: Text(widget.title),
      content: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.7,
          maxWidth: 500,
        ),
        child: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: children,
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: widget.onEdit, child: const Text('edit')),
        TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('close')),
      ],
    );
  }

  Widget _sectionHeader(String text) => Padding(
        padding: const EdgeInsets.only(top: 4, bottom: 2),
        child: Text(text,
            style:
                const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
      );

  Widget _notesWidget(String notes) => Container(
        width: double.infinity,
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.grey[100],
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(notes.trimRight(),
            style: const TextStyle(fontSize: 13, color: Colors.black87)),
      );

  Widget _bullet(InlineSpan content, {double indent = 0}) => Padding(
        padding: EdgeInsets.only(left: indent, top: 2, bottom: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('•  '),
            Expanded(
              child: RichText(
                text: TextSpan(
                  style: const TextStyle(
                      color: Colors.black, fontSize: 14, height: 1.3),
                  children: [content],
                ),
              ),
            ),
          ],
        ),
      );

  Widget _ingredientWidget(dynamic ing) {
    if (ing is String) {
      return _bullet(TextSpan(text: ing));
    }
    if (ing is! Map) return const SizedBox.shrink();

    final amount = _ingredientAmount(ing, _scale);
    final item = (ing['item'] ?? '').toString();
    final note = ing['note']?.toString();
    final optional = ing['optional'] == true;
    final isBasis = ing['basis'] == true;

    final spans = <InlineSpan>[];
    if (amount.isNotEmpty) {
      spans.add(TextSpan(
        text: '$amount ',
        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue[800]),
      ));
    }
    spans.add(TextSpan(text: item));
    if (optional) {
      spans.add(const TextSpan(
        text: ' (optional)',
        style: TextStyle(color: Colors.black45, fontStyle: FontStyle.italic),
      ));
    }
    if (note != null && note.trim().isNotEmpty) {
      spans.add(TextSpan(
        text: ' — $note',
        style:
            const TextStyle(color: Colors.black54, fontStyle: FontStyle.italic),
      ));
    }
    if (isBasis) {
      spans.add(const TextSpan(
        text: '  ⚖',
        style: TextStyle(color: Colors.blue),
      ));
    }
    return _bullet(TextSpan(children: spans));
  }

  List<Widget> _stepWidgets(List steps) {
    final widgets = <Widget>[];
    for (final s in steps) {
      if (s is String) {
        widgets.add(_bullet(TextSpan(text: s)));
      } else if (s is Map) {
        widgets.add(_bullet(TextSpan(text: (s['step'] ?? '').toString())));
        final subs = s['substeps'];
        if (subs is List) {
          for (final sub in subs) {
            widgets.add(_bullet(TextSpan(text: sub.toString()), indent: 22));
          }
        }
      }
    }
    return widgets;
  }
}

/// Raw-YAML editor with debounced autosave. Edits persist as you type (after a
/// short pause) and are flushed on close, so tapping away never loses progress.
class RecipeEditDialog extends StatefulWidget {
  const RecipeEditDialog({
    super.key,
    required this.recipeId,
    required this.initialContent,
    required this.onSave,
  });

  final String recipeId;
  final String initialContent;
  final Future<bool> Function(String content) onSave;

  @override
  State<RecipeEditDialog> createState() => _RecipeEditDialogState();
}

class _RecipeEditDialogState extends State<RecipeEditDialog> {
  late final TextEditingController _controller;
  Timer? _debounce;
  String _lastSaved = '';
  String _status = '';

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialContent);
    _lastSaved = widget.initialContent;
  }

  @override
  void dispose() {
    _debounce?.cancel();
    // Flush any unsaved edits on close (covers tap-away / back button).
    if (_controller.text != _lastSaved) {
      widget.onSave(_controller.text);
    }
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String _) {
    setState(() => _status = 'unsaved');
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 900), _flush);
  }

  Future<void> _flush() async {
    final text = _controller.text;
    if (text == _lastSaved) return;
    if (mounted) setState(() => _status = 'saving…');
    final ok = await widget.onSave(text);
    _lastSaved = text;
    if (mounted) setState(() => _status = ok ? 'saved ✓' : 'save failed');
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          Expanded(child: Text('Edit: ${widget.recipeId}')),
          Text(
            _status,
            style: TextStyle(
              fontSize: 12,
              color: _status == 'save failed' ? Colors.red : Colors.black54,
            ),
          ),
        ],
      ),
      content: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.6,
          maxWidth: 600,
        ),
        child: SizedBox(
          width: 600,
          child: TextField(
            controller: _controller,
            maxLines: null,
            expands: true,
            keyboardType: TextInputType.multiline,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
            decoration: const InputDecoration(border: OutlineInputBorder()),
            onChanged: _onChanged,
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () async {
            _debounce?.cancel();
            await _flush();
            if (mounted) Navigator.pop(context);
          },
          child: const Text('done'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Recipes browser: grouped/searchable list  <->  reference/ingredient graph
// ---------------------------------------------------------------------------

const List<Color> _kCategoryPalette = [
  Color(0xFFE57373), Color(0xFF64B5F6), Color(0xFF81C784), Color(0xFFFFB74D),
  Color(0xFFBA68C8), Color(0xFF4DB6AC), Color(0xFFA1887F), Color(0xFF90A4AE),
  Color(0xFFF06292), Color(0xFF7986CB), Color(0xFFAED581), Color(0xFFFFD54F),
  Color(0xFF4FC3F7), Color(0xFFFF8A65), Color(0xFF9575CD), Color(0xFF4DD0E1),
  Color(0xFFDCE775), Color(0xFFFFB300), Color(0xFF26A69A),
];

Color _categoryColor(String category, List<String> categories) {
  final i = categories.indexOf(category);
  if (i < 0) return Colors.grey;
  return _kCategoryPalette[i % _kCategoryPalette.length];
}

enum _RecipeView { list, graph }

/// The Recipes page: a List ⇄ Graph toggle over the recipe index.
class RecipesPage extends StatefulWidget {
  const RecipesPage({
    super.key,
    required this.index,
    required this.fallbackPaths,
    required this.onOpen,
  });

  final List<Map<String, dynamic>> index;
  final List<String> fallbackPaths;
  final void Function(String path) onOpen;

  @override
  State<RecipesPage> createState() => _RecipesPageState();
}

class _RecipesPageState extends State<RecipesPage> {
  _RecipeView _view = _RecipeView.list;
  String _query = '';
  bool _scalableOnly = false;
  final Set<String> _expandedCats = {};
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// Rich index when available, else minimal entries built from plain paths.
  List<Map<String, dynamic>> get _entries {
    if (widget.index.isNotEmpty) return widget.index;
    return widget.fallbackPaths
        .map((p) => <String, dynamic>{
              'path': p,
              'category': p.contains('/') ? p.split('/').first : '',
              'name': p.split('/').last.replaceAll('-', ' '),
              'hasBasis': false,
              'ingredients': const <String>[],
              'refs': const <String>[],
            })
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final entries = _entries;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Recipes'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: SegmentedButton<_RecipeView>(
              segments: const [
                ButtonSegment(
                    value: _RecipeView.list,
                    icon: Icon(Icons.list),
                    label: Text('List')),
                ButtonSegment(
                    value: _RecipeView.graph,
                    icon: Icon(Icons.hub),
                    label: Text('Graph')),
              ],
              selected: {_view},
              showSelectedIcon: false,
              onSelectionChanged: (s) => setState(() => _view = s.first),
            ),
          ),
        ],
      ),
      body: entries.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : (_view == _RecipeView.list
              ? _buildList(entries)
              : RecipeGraphView(index: entries, onOpen: widget.onOpen)),
    );
  }

  Widget _buildList(List<Map<String, dynamic>> entries) {
    final q = _query.toLowerCase().trim();
    bool matches(Map<String, dynamic> r) {
      if (_scalableOnly && r['hasBasis'] != true) return false;
      if (q.isEmpty) return true;
      final hay = StringBuffer()
        ..write((r['path'] ?? '').toString().toLowerCase())
        ..write(' ')
        ..write((r['name'] ?? '').toString().toLowerCase());
      for (final i in (r['ingredients'] as List? ?? const [])) {
        hay
          ..write(' ')
          ..write(i.toString().toLowerCase());
      }
      return hay.toString().contains(q);
    }

    final filtered = entries.where(matches).toList();
    final byCat = <String, List<Map<String, dynamic>>>{};
    for (final r in filtered) {
      final c = (r['category'] ?? '').toString();
      byCat.putIfAbsent(c.isEmpty ? 'other' : c, () => []).add(r);
    }
    final cats = byCat.keys.toList()..sort();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'search name or ingredient…',
              prefixIcon: const Icon(Icons.search),
              isDense: true,
              border: const OutlineInputBorder(),
              suffixIcon: _query.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _query = '');
                      },
                    ),
            ),
            onChanged: (v) => setState(() => _query = v),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              FilterChip(
                label: const Text('⚖ scalable'),
                selected: _scalableOnly,
                onSelected: (v) => setState(() => _scalableOnly = v),
              ),
              const Spacer(),
              Builder(builder: (context) {
                final allExpanded =
                    cats.isNotEmpty && _expandedCats.containsAll(cats);
                return TextButton.icon(
                  icon: Icon(
                      allExpanded ? Icons.unfold_less : Icons.unfold_more,
                      size: 18),
                  label: Text(allExpanded ? 'collapse all' : 'expand all'),
                  onPressed: cats.isEmpty
                      ? null
                      : () => setState(() {
                            if (allExpanded) {
                              _expandedCats.removeAll(cats);
                            } else {
                              _expandedCats.addAll(cats);
                            }
                          }),
                );
              }),
            ],
          ),
        ),
        Expanded(
          child: filtered.isEmpty
              ? const Center(child: Text('no matches'))
              : ListView(
                  children: [
                    for (final c in cats) ...[
                      _categoryHeader(c, byCat[c]!.length,
                          q.isNotEmpty || _expandedCats.contains(c)),
                      if (q.isNotEmpty || _expandedCats.contains(c))
                        for (final r in byCat[c]!)
                          ListTile(
                            dense: true,
                            contentPadding:
                                const EdgeInsets.only(left: 32, right: 16),
                            title: Text(_displayLabel(r)),
                            trailing: r['hasBasis'] == true
                                ? const Text('⚖',
                                    style: TextStyle(color: Colors.blue))
                                : null,
                            onTap: () => widget.onOpen((r['path']).toString()),
                          ),
                    ],
                  ],
                ),
        ),
      ],
    );
  }

  Widget _categoryHeader(String category, int count, bool expanded) {
    return InkWell(
      onTap: () => setState(() {
        if (_expandedCats.contains(category)) {
          _expandedCats.remove(category);
        } else {
          _expandedCats.add(category);
        }
      }),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Icon(expanded ? Icons.expand_more : Icons.chevron_right, size: 20),
            const SizedBox(width: 8),
            Text('$category  ($count)',
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  String _displayLabel(Map<String, dynamic> r) {
    final path = (r['path'] ?? '').toString();
    final cat = (r['category'] ?? '').toString();
    if (cat.isNotEmpty && path.startsWith('$cat/')) {
      return path.substring(cat.length + 1);
    }
    return path;
  }
}

/// Force-directed graph of recipes. Nodes are coloured by category; edges are
/// explicit cross-references (strong) plus shared distinctive ingredients
/// (weak). Pan/zoom via InteractiveViewer; tap a node to open the recipe.
class RecipeGraphView extends StatefulWidget {
  const RecipeGraphView({super.key, required this.index, required this.onOpen});

  final List<Map<String, dynamic>> index;
  final void Function(String path) onOpen;

  @override
  State<RecipeGraphView> createState() => _RecipeGraphViewState();
}

class _RecipeGraphViewState extends State<RecipeGraphView> {
  double _w = 1000;
  double _h = 1000;

  List<_GNode> _nodes = [];
  List<_GEdge> _edges = [];
  List<String> _categories = [];
  List<_ClusterLabel> _labels = [];

  final TransformationController _tc = TransformationController();
  bool _fitted = false;
  bool _showSimilarity = false;

  @override
  void initState() {
    super.initState();
    _layout();
  }

  @override
  void didUpdateWidget(RecipeGraphView old) {
    super.didUpdateWidget(old);
    if (old.index.length != widget.index.length) {
      _fitted = false;
      _layout();
    }
  }

  @override
  void dispose() {
    _tc.dispose();
    super.dispose();
  }

  void _layout() {
    final entries = widget.index;
    final n = entries.length;
    _categories = entries
        .map((e) => (e['category'] ?? '').toString())
        .toSet()
        .toList()
      ..sort();

    final idxOf = <String, int>{};
    for (var i = 0; i < n; i++) {
      idxOf[(entries[i]['path']).toString()] = i;
    }

    final edgeKeys = <String>{};
    final edges = <_GEdge>[];
    void addEdge(int a, int b, bool strong) {
      if (a == b) return;
      final key = a < b ? '$a-$b' : '$b-$a';
      if (edgeKeys.add(key)) edges.add(_GEdge(a, b, strong));
    }

    // Strong edges: explicit `uses:` sub-recipe links (curated in the YAML).
    for (var i = 0; i < n; i++) {
      for (final r in (entries[i]['uses'] as List? ?? const [])) {
        final j = idxOf[r.toString()];
        if (j != null) addEdge(i, j, true);
      }
    }

    // Weak edges (optional overlay): pairs sharing >=3 distinctive ingredients
    // (doc-frequency in 2..8). Off by default — toggled by the user.
    if (_showSimilarity) {
      final df = <String, int>{};
      for (final e in entries) {
        for (final i in (e['ingredients'] as List? ?? const [])) {
          df[i.toString()] = (df[i.toString()] ?? 0) + 1;
        }
      }
      final inverted = <String, List<int>>{};
      for (var i = 0; i < n; i++) {
        for (final ing in (entries[i]['ingredients'] as List? ?? const [])) {
          final c = df[ing.toString()] ?? 0;
          if (c >= 2 && c <= 8) {
            inverted.putIfAbsent(ing.toString(), () => []).add(i);
          }
        }
      }
      final shared = <String, int>{};
      for (final members in inverted.values) {
        for (var x = 0; x < members.length; x++) {
          for (var y = x + 1; y < members.length; y++) {
            final a = members[x], b = members[y];
            final key = a < b ? '$a-$b' : '$b-$a';
            shared[key] = (shared[key] ?? 0) + 1;
          }
        }
      }
      shared.forEach((key, count) {
        if (count >= 3) {
          final parts = key.split('-');
          addEdge(int.parse(parts[0]), int.parse(parts[1]), false);
        }
      });
    }

    // --- positions: pack each category into its own disk, clusters on a grid
    final byCat = <String, List<int>>{};
    for (var i = 0; i < n; i++) {
      byCat
          .putIfAbsent((entries[i]['category'] ?? '').toString(), () => [])
          .add(i);
    }

    const baseR = 30.0; // cluster radius scales with sqrt(member count)
    const gap = 130.0; // space between cluster bounding circles
    final radius = <String, double>{};
    double maxR = 1;
    for (final c in _categories) {
      final r = baseR * sqrt((byCat[c]?.length ?? 1).toDouble());
      radius[c] = r;
      maxR = max(maxR, r);
    }

    final cols = max(1, sqrt(_categories.length).ceil());
    final rows = max(1, (_categories.length / cols).ceil());
    final cell = 2 * maxR + gap;
    _w = cols * cell;
    _h = rows * cell;

    final nodes = List.generate(n, (i) {
      return _GNode(
        path: (entries[i]['path']).toString(),
        label: (entries[i]['path'])
            .toString()
            .split('/')
            .last
            .replaceAll('-', ' '),
        category: (entries[i]['category'] ?? '').toString(),
        x: 0,
        y: 0,
      );
    });

    // Phyllotaxis (sunflower) packing gives an even disk of nodes per cluster.
    final golden = pi * (3 - sqrt(5));
    final labels = <_ClusterLabel>[];
    for (var ci = 0; ci < _categories.length; ci++) {
      final c = _categories[ci];
      final members = byCat[c] ?? const [];
      final cx = (ci % cols) * cell + cell / 2;
      final cy = (ci ~/ cols) * cell + cell / 2;
      final r = radius[c] ?? baseR;
      labels.add(_ClusterLabel(
        text: c.isEmpty ? 'other' : c,
        x: cx,
        y: cy - r - 22,
        color: _categoryColor(c, _categories),
      ));
      for (var k = 0; k < members.length; k++) {
        final nr =
            members.length <= 1 ? 0.0 : r * sqrt((k + 0.5) / members.length);
        final ang = k * golden;
        nodes[members[k]].x = cx + nr * cos(ang);
        nodes[members[k]].y = cy + nr * sin(ang);
      }
    }

    _nodes = nodes;
    _edges = edges;
    _labels = labels;
  }

  /// On first layout, fit the whole graph to the viewport.
  void _maybeFit(BoxConstraints c) {
    if (_fitted || _w <= 0 || !c.maxWidth.isFinite || !c.maxHeight.isFinite) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _fitted) return;
      final s = min(c.maxWidth / _w, c.maxHeight / _h) * 0.92;
      _tc.value = Matrix4.identity()
        ..translate((c.maxWidth - _w * s) / 2, (c.maxHeight - _h * s) / 2)
        ..scale(s, s, 1.0);
      _fitted = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        LayoutBuilder(builder: (context, constraints) {
          _maybeFit(constraints);
          return InteractiveViewer(
            transformationController: _tc,
            constrained: false,
            minScale: 0.05,
            maxScale: 4,
            boundaryMargin: const EdgeInsets.all(400),
            child: SizedBox(
              width: _w,
              height: _h,
              child: Stack(
                children: [
                  CustomPaint(
                    size: Size(_w, _h),
                    painter: _GraphEdgePainter(_nodes, _edges),
                  ),
                  for (final label in _labels)
                    Positioned(
                      left: label.x - 60,
                      top: label.y,
                      width: 120,
                      child: Text(
                        label.text,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: label.color,
                        ),
                      ),
                    ),
                  for (final node in _nodes)
                    Positioned(
                      left: node.x - 6,
                      top: node.y - 6,
                      child: GestureDetector(
                        onTap: () => widget.onOpen(node.path),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 12,
                              height: 12,
                              decoration: BoxDecoration(
                                color:
                                    _categoryColor(node.category, _categories),
                                shape: BoxShape.circle,
                                border:
                                    Border.all(color: Colors.white, width: 1),
                              ),
                            ),
                            Text(node.label,
                                style: const TextStyle(fontSize: 7)),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          );
        }),
        Positioned(
          left: 8,
          top: 8,
          child: Card(
            color: Colors.white.withOpacity(0.85),
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final c in _categories)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      Container(
                          width: 8,
                          height: 8,
                          color: _categoryColor(c, _categories)),
                      const SizedBox(width: 4),
                      Text(c.isEmpty ? 'other' : c,
                          style: const TextStyle(fontSize: 9)),
                    ]),
                ],
              ),
            ),
          ),
        ),
        Positioned(
          right: 8,
          top: 8,
          child: FilterChip(
            backgroundColor: Colors.white.withOpacity(0.85),
            label: const Text('ingredient links',
                style: TextStyle(fontSize: 11)),
            selected: _showSimilarity,
            onSelected: (v) => setState(() {
              _showSimilarity = v;
              _layout();
            }),
          ),
        ),
      ],
    );
  }
}

class _GNode {
  _GNode({
    required this.path,
    required this.label,
    required this.category,
    required this.x,
    required this.y,
  });

  final String path;
  final String label;
  final String category;
  double x;
  double y;
}

class _GEdge {
  _GEdge(this.a, this.b, this.strong);
  final int a;
  final int b;
  final bool strong;
}

class _ClusterLabel {
  _ClusterLabel({
    required this.text,
    required this.x,
    required this.y,
    required this.color,
  });

  final String text;
  final double x;
  final double y;
  final Color color;
}

class _GraphEdgePainter extends CustomPainter {
  _GraphEdgePainter(this.nodes, this.edges);

  final List<_GNode> nodes;
  final List<_GEdge> edges;

  @override
  void paint(Canvas canvas, Size size) {
    final weak = Paint()
      ..color = Colors.grey.withOpacity(0.25)
      ..strokeWidth = 0.6;
    final strong = Paint()
      ..color = Colors.blueGrey.withOpacity(0.6)
      ..strokeWidth = 1.4;
    for (final e in edges) {
      final a = nodes[e.a], b = nodes[e.b];
      canvas.drawLine(
          Offset(a.x, a.y), Offset(b.x, b.y), e.strong ? strong : weak);
    }
  }

  @override
  bool shouldRepaint(_GraphEdgePainter old) =>
      old.nodes != nodes || old.edges != edges;
}
