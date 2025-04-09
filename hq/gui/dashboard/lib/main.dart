// import 'package:flutter/material.dart';

// void main() {
//   runApp(const MyApp());
// }

// class MyApp extends StatelessWidget {
//   const MyApp({super.key});

//   // This widget is the root of your application.
//   @override
//   Widget build(BuildContext context) {
//     return MaterialApp(
//       title: 'Flutter Demo',
//       theme: ThemeData(
//         // This is the theme of your application.
//         //
//         // TRY THIS: Try running your application with "flutter run". You'll see
//         // the application has a purple toolbar. Then, without quitting the app,
//         // try changing the seedColor in the colorScheme below to Colors.green
//         // and then invoke "hot reload" (save your changes or press the "hot
//         // reload" button in a Flutter-supported IDE, or press "r" if you used
//         // the command line to start the app).
//         //
//         // Notice that the counter didn't reset back to zero; the application
//         // state is not lost during the reload. To reset the state, use hot
//         // restart instead.
//         //
//         // This works for code too, not just values: Most code changes can be
//         // tested with just a hot reload.
//         colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
//         useMaterial3: true,
//       ),
//       home: const MyHomePage(title: 'Flutter Demo Home Page'),
//     );
//   }
// }

// class MyHomePage extends StatefulWidget {
//   const MyHomePage({super.key, required this.title});

//   // This widget is the home page of your application. It is stateful, meaning
//   // that it has a State object (defined below) that contains fields that affect
//   // how it looks.

//   // This class is the configuration for the state. It holds the values (in this
//   // case the title) provided by the parent (in this case the App widget) and
//   // used by the build method of the State. Fields in a Widget subclass are
//   // always marked "final".

//   final String title;

//   @override
//   State<MyHomePage> createState() => _MyHomePageState();
// }

// class _MyHomePageState extends State<MyHomePage> {
//   int _counter = 0;

//   void _incrementCounter() {
//     setState(() {
//       // This call to setState tells the Flutter framework that something has
//       // changed in this State, which causes it to rerun the build method below
//       // so that the display can reflect the updated values. If we changed
//       // _counter without calling setState(), then the build method would not be
//       // called again, and so nothing would appear to happen.
//       _counter++;
//     });
//   }

//   @override
//   Widget build(BuildContext context) {
//     // This method is rerun every time setState is called, for instance as done
//     // by the _incrementCounter method above.
//     //
//     // The Flutter framework has been optimized to make rerunning build methods
//     // fast, so that you can just rebuild anything that needs updating rather
//     // than having to individually change instances of widgets.
//     return Scaffold(
//       appBar: AppBar(
//         // TRY THIS: Try changing the color here to a specific color (to
//         // Colors.amber, perhaps?) and trigger a hot reload to see the AppBar
//         // change color while the other colors stay the same.
//         backgroundColor: Theme.of(context).colorScheme.inversePrimary,
//         // Here we take the value from the MyHomePage object that was created by
//         // the App.build method, and use it to set our appbar title.
//         title: Text(widget.title),
//       ),
//       body: Center(
//         // Center is a layout widget. It takes a single child and positions it
//         // in the middle of the parent.
//         child: Column(
//           // Column is also a layout widget. It takes a list of children and
//           // arranges them vertically. By default, it sizes itself to fit its
//           // children horizontally, and tries to be as tall as its parent.
//           //
//           // Column has various properties to control how it sizes itself and
//           // how it positions its children. Here we use mainAxisAlignment to
//           // center the children vertically; the main axis here is the vertical
//           // axis because Columns are vertical (the cross axis would be
//           // horizontal).
//           //
//           // TRY THIS: Invoke "debug painting" (choose the "Toggle Debug Paint"
//           // action in the IDE, or press "p" in the console), to see the
//           // wireframe for each widget.
//           mainAxisAlignment: MainAxisAlignment.center,
//           children: <Widget>[
//             const Text(
//               'You have pushed the button this many times:',
//             ),
//             Text(
//               '$_counter',
//               style: Theme.of(context).textTheme.headlineMedium,
//             ),
//           ],
//         ),
//       ),
//       floatingActionButton: FloatingActionButton(
//         onPressed: _incrementCounter,
//         tooltip: 'Increment',
//         child: const Icon(Icons.add),
//       ), // This trailing comma makes auto-formatting nicer for build methods.
//     );
//   }
// }


// // //

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  static const appTitle = 'Emily';

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
  static const List<Widget> _widgetOptions = <Widget>[
    Text(
      'Dashboard',
      style: optionStyle,
    ),
    Text(
      'Recipes',
      style: optionStyle,
    ),
    Text(
      'Relationship counter',
      style: optionStyle,
    ),
    Text(
      'Why is Emily so great?',
      style: optionStyle,
    ),
    Text(
      'Reviews',
      style: optionStyle,
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
    final response = await http.get(Uri.parse('http://192.168.0.247:8000/recipes'), headers: {
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
          await http.get(Uri.parse('http://127.0.0.1:8000/recipes/$denestedRecipeId'));

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
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/relationship_time'));

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
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/why_emily_is_great'));

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

  void _showBirthdayDialog() {
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
                  'You\'ve achieved so much this year, I\'m so proud of you! You have surpassed most commercial food establishments, despite the oven; grown the family considerably (particularly in the sighthound direction); and started on the path of being a veterinary mogul of Wagga; just to name a few!'
                 style: TextStyle(fontSize: 14),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                const Text(
                  'I love our life together, so planning for and building our future is the most exciting and rewarding project I have ever been a part of. I am perpetually honoured you chose me, because you are the most amazing person I have ever met. You have your shit more together than most people I know, regardless of age, and you always think for yourself; which alone make you a force to be reckoned with. I am not surprised one bit that they see you as a suitable succession plan for the clinic!',
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
          Center(
            child: _widgetOptions.elementAt(_selectedIndex),
          ),
          Positioned(
            right: 16,
            bottom: 16,
            child: GestureDetector(
              onTap: _showBirthdayDialog,
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
              title: const Text('Dashboard'),
              selected: _selectedIndex == 0,
              onTap: () {
                // Update the state of the app
                _onItemTapped(0);
                // Then close the drawer
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: const Text('Recipes'),
              selected: _selectedIndex == 1,
              onTap: () {
                // Update the state of the app
                _onItemTapped(1);

                // // Query the API for recipes (doesn't work)
                // fetchRecipes();

                // Then close the drawer
                Navigator.pop(context);

                // Draw the recipes
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => Scaffold(
                      appBar: AppBar(
                        title: Text('Recipes'),
                      ),
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
                  ),
                );
              },
            ),
            ListTile(
              title: const Text('Relationship counter'),
              selected: _selectedIndex == 2,
              onTap: () {
                // Update the state of the app
                _onItemTapped(2);
                // Then close the drawer
                Navigator.pop(context);
                // Now query the relationship time
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => Scaffold(
                      appBar: AppBar(
                        title: Text('Relationship time'),
                      ),
                      body: Center(
                        child: ElevatedButton(
                          onPressed: fetchRelationshipTime,
                          child: const Text('Get relationship time'),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            ListTile(
              title: const Text('Why is Emily so great?'),
              selected: _selectedIndex == 3,
              onTap: () {
                // Update the state of the app
                _onItemTapped(3);
                //
                // Then close the drawer
                Navigator.pop(context);

                // Now query why Emily is great
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => Scaffold(
                      appBar: AppBar(
                        title: Text('Why is Emily so great?'),
                      ),
                      body: Center(
                        child: ElevatedButton(
                          onPressed: fetchWhyEmilyIsGreat,
                          child: const Text('Go on then, tell me'),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            ListTile(
              title: const Text('Reviews'),
              selected: _selectedIndex == 4,
              onTap: () {
                // Update the state of the app
                _onItemTapped(4);
                // Show an "in progress" message
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Reviews still under development...'),
                  ),
                );
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
