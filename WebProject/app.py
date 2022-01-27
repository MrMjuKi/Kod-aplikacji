from flask import Flask, render_template, request, session
from flask.templating import render_template_string
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)

app.secret_key = 'klucz'
  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'daza_danych_ofert'
  
mysql = MySQL(app)

def listaOfert(IDuzytkownika):
    listaOfert = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if IDuzytkownika != 'ANY':
        listaOfert.execute('SELECT uzytkownik.login, oferta.nazwa_produktu, oferta.opis, oferta.liczba_sztuk, oferta.cena, oferta.ID_oferty FROM oferta INNER JOIN uzytkownik ON oferta.ID_uzytkownika=uzytkownik.ID_uzytkownika WHERE oferta.ID_uzytkownika = % s', (str(IDuzytkownika)))
    else:
        listaOfert.execute('SELECT uzytkownik.login, oferta.nazwa_produktu, oferta.opis, oferta.liczba_sztuk, oferta.cena FROM oferta INNER JOIN uzytkownik ON oferta.ID_uzytkownika=uzytkownik.ID_uzytkownika')

    mysql.connection.commit()
    listaOfert.close()
    
    return listaOfert

@app.route('/')
@app.route('/home')
def index():
    if session:
        return render_template('index.html', listaOfert=listaOfert('ANY'))

    return render_template('index.html', msg="Zaloguj sie w celu przegladania ofert")

@app.route('/rejestracja', methods=['GET', 'POST'])
def rejestracja():
    if session:
        return render_template('index.html',listaOfert=listaOfert('ANY'), msg ='Jestes juz zalogowany jako ' + str(session['username']))

    if request.method == 'POST':
        uzytkownik = request.form.get('inputUzytkownik')
        email = request.form.get('inputEmail')
        haslo = request.form.get('inputHaslo')

        tworzenieKonta = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        tworzenieKonta.execute('BEGIN; INSERT INTO uzytkownik (login, haslo) VALUES ( % s, % s); INSERT INTO personalia (ID_uzytkownika, `e-mail`) VALUES (last_insert_id(), % s); COMMIT;', (uzytkownik, haslo, email ))
        #mysql.connection.commit
        
        return render_template('index.html',listaOfert=listaOfert('ANY') ,msg ='Rejestracja przebiegla pomyslnie. Teraz mozesz sie zalogowac')

    return render_template('rejestracja.html')

@app.route('/logowanie', methods=['GET', 'POST'])
def logowanie():
    if session:
        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Jestes juz zalogowany jako ' + str(session['username']))

    if request.method == 'POST':
        uzytkownik = request.form.get('inputUzytkownik')
        haslo = request.form.get('inputHaslo')

        probaLogowania = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        probaLogowania.execute('SELECT * FROM uzytkownik WHERE login = % s AND haslo = % s', (uzytkownik, haslo ))

        konto = probaLogowania.fetchone()
        if konto:
            session['id'] = konto['ID_uzytkownika']
            session['username'] = konto['login']
            return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Udalo sie zalogowac. Witaj ' + session['username'])
        else:
            return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Nie udalo sie zalogowac. Wpisales zle haslo lub login.')

    return render_template('logowanie.html')

@app.route('/wyloguj')
def wyloguj():
    if not session:
        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Nie jestes zalogowany na zadne konto')

    session.pop('id', None)
    session.pop('username', None)

    return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Wylogowanie przebieglo pomyslnie')

@app.route('/dodajOferte', methods=['GET', 'POST'])
def dodawanieOferty():
    if not session:
        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Zaloguj sie lub utworz konto, by dodac oferte')

    if request.method == 'POST':
        nazwaProduktu = request.form.get('inputNameOfProduct')
        opis = request.form.get('inputDescription')
        ilosc = request.form.get('inputAmount')
        cena = request.form.get('inputPrice')

        dodanieOferty = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        dodanieOferty.execute('INSERT INTO oferta (ID_uzytkownika, nazwa_produktu, opis, liczba_sztuk, cena) VALUES ( % s, % s, % s, % s, % s)', (session['id'], nazwaProduktu, opis, ilosc, cena ))

        mysql.connection.commit()

        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Pomyslnie dodano produkt')

    return render_template('/dodawanieoferty.html')

@app.route('/mojeOferty', methods=['GET', 'POST'])
def mojeoferty():
    if not session:
        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Zaloguj sie, by zobaczyc swoje oferty')    
    
    if request.method == 'POST':
        usunOferte = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        usunOferte.execute('DELETE FROM oferta WHERE ID_oferty = % s', (str(request.form.get('usun'))))

        mysql.connection.commit()
        return render_template('index.html' ,msg= 'Oferta zostala usunieta' ,listaOfert=listaOfert('ANY'))

    return render_template('mojeOferty.html' ,listaOfert=listaOfert(session['id']))

@app.route('/mojeDane', methods=['GET', 'POST'])
def mojeDane():
    if not session:
        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Zaloguj sie, by zobaczyc swoje dane')

    if request.method == 'POST':
        imie = request.form.get('inputName')
        nazwisko = request.form.get('inputSurname')
        telefon = request.form.get('inputNumber')
        if telefon == 'None':
            telefon = 0
        email = request.form.get('inputEmail')

        aktualizacjaDanych = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        aktualizacjaDanych.execute('UPDATE personalia SET imie = % s, nazwisko = % s, nr_telefonu = % s, `e-mail` = % s WHERE ID_uzytkownika = % s', (imie, nazwisko, telefon, email, str(session['id']) ))

        mysql.connection.commit()

        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Zmiany zapisano')


    mojeDane = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    mojeDane.execute('SELECT imie, nazwisko, nr_telefonu, `e-mail` FROM personalia WHERE ID_uzytkownika = % s', (str(session['id'])))
    mysql.connection.commit()
    mojeDane.close()
    

    return render_template('mojeDane.html', mojeDane=mojeDane)



if __name__ == '__main__':
    app.run('0.0.0.0', 4449)