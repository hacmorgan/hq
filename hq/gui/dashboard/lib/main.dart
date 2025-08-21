import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

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
  int _selectedIndex = 0;
  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  List<Widget> _widgetOptions() => <Widget>[
    // Recipes page
    Scaffold(
      appBar: AppBar(title: const Text('Recipes')),
      body: ListView.builder(
        itemCount: recipes.length,
        itemBuilder: (context, index) {
          return ListTile(
            title: Text(recipes[index]),
            onTap: () {
              _fetchRecipeDetails(recipes[index]);
            },
          );
        },
      ),
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
  }

  Future<void> fetchRecipes() async {
    final response = await http.get(Uri.parse('http://192.168.0.247:10498/recipes'), headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      });
    if (response.statusCode == 200) {
      setState(() {
        recipes = List<String>.from(json.decode(response.body));
      });
    } else {
      throw Exception('Failed to load recipes');
    }
  }

  // Function to fetch and display recipe details
  Future<void> _fetchRecipeDetails(String recipeId) async {
    try {
      String denestedRecipeId = recipeId.replaceAll("/", "..");
      final response =
          await http.get(Uri.parse('http://192.168.0.247:10498/recipes/$denestedRecipeId'));

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        // Display the recipe details, for example, in a dialog or a new screen
        showDialog(
            context: context,
            builder: (context) {
              return AlertDialog(
                title: Text(data["name"]),
                content: Text(data["recipe"]), // Or whatever info is returned
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text("close"))
                ],
              );
            });
      } else {
        throw Exception('Failed to load recipe details');
      }
    } catch (e) {
      print('Error fetching recipe details: $e');
    }
  }

  Future<void> fetchRelationshipTime() async {
    // Query the API for relationship time
    try {
      final response = await http.get(Uri.parse('http://192.168.0.247:10498/relationship_time'));

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        // Display the relationship time, for example, in a dialog or a new screen
        showDialog(
            context: context,
            builder: (context) {
              return AlertDialog(
                title: const Text("Relationship time"),
                content: Text(data["time"]), // Or whatever info is returned
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
    // Query the API for why Emily is great
    try {
      final response = await http.get(Uri.parse('http://192.168.0.247:10498/why_emily_is_great'));

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        // Display why Emily is great, for example, in a dialog or a new screen
        showDialog(
            context: context,
            builder: (context) {
              return AlertDialog(
                title: const Text("One reason is:"),
                content: Text(data["reason"]), // Or whatever info is returned
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
          content: SingleChildScrollView(
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
          content: SingleChildScrollView(
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
          content: SingleChildScrollView(
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
            bottom: 160,
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
            bottom: 88,
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
            bottom: 16,
            child: GestureDetector(
              onTap: _show3kMilleniversaryDialog,
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
