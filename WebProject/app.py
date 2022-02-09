from flask import Flask, render_template, request, session
from flask.templating import render_template_string
from flask_mysqldb import MySQL
import MySQLdb.cursors

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import re

from hashlib import blake2b

app = Flask(__name__)
limiter = Limiter(app, key_func=get_remote_address)
app.secret_key = 'klucz'
  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'baza_danych_ofert'
  
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
        
        if not uzytkownik.isalnum():
            return render_template('index.html', msg ='Zla nazwa uzytkownika')

        if not re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email):
            return render_template('index.html', msg ='Zly e-mail')
        
        if not haslo:
            return render_template('index.html', msg ='Uzupelnij pole haslo')

        szukanieEmailu = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        szukanieEmailu.execute('SELECT `e-mail` FROM personalia WHERE `e-mail` =  % s', [email])
        mysql.connection.commit
        if szukanieEmailu.fetchone():
            return render_template('index.html', msg ='Konto o podanym e-mailu istnieje')

        szukanieLoginu = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        szukanieLoginu.execute('SELECT * FROM uzytkownik WHERE login =  % s', [uzytkownik])
        mysql.connection.commit
        if szukanieLoginu.fetchone():
            return render_template('index.html', msg ='Konto o podanym loginie istnieje')

        if not re.search('[!@#$%^&*()\-_=+[{\]}\\|;:/?.>,<]', haslo) or not re.search('[a-z]', haslo) or  not re.search('[A-Z]', haslo) or not re.search('[0-9]', haslo) or len(haslo)<8:
            return render_template('index.html', msg ='Zbyt slabe haslo')

        hashHaslo = blake2b(('b'+haslo).encode('utf-8')).hexdigest()

        tworzenieKonta = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        tworzenieKonta.execute('BEGIN; INSERT INTO uzytkownik (login, haslo) VALUES ( % s, % s); INSERT INTO personalia (ID_uzytkownika, `e-mail`) VALUES (last_insert_id(), % s); COMMIT;', (uzytkownik, hashHaslo, email ))
        
        
        return render_template('index.html' ,msg ='Rejestracja przebiegla pomyslnie. Teraz mozesz sie zalogowac')

    return render_template('rejestracja.html')

@app.route('/logowanie', methods=['GET', 'POST'])
@limiter.limit("5/hour", error_message='Osiagnieto limit pieciu prob zalogowania sie. Sprobuj za godzine')
def logowanie():
    if session:
        return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Jestes juz zalogowany jako ' + str(session['username']))

    if request.method == 'POST':
        uzytkownik = request.form.get('inputUzytkownik')
        haslo = request.form.get('inputHaslo')
        hashHaslo = blake2b(('b'+haslo).encode('utf-8')).hexdigest()

        probaLogowania = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        probaLogowania.execute('SELECT * FROM uzytkownik WHERE login = % s AND haslo = % s', (uzytkownik, hashHaslo ))

        konto = probaLogowania.fetchone()
        if konto:
            session['id'] = konto['ID_uzytkownika']
            session['username'] = konto['login']
            return render_template('index.html' ,listaOfert=listaOfert('ANY'), msg ='Udalo sie zalogowac. Witaj ' + session['username'])
        else:
            return render_template('index.html', msg ='Nie udalo sie zalogowac. Wpisales zle haslo lub login.')

    return render_template('logowanie.html')

@app.route('/wyloguj')
def wyloguj():
    if not session:
        return render_template('index.html', msg ='Nie jestes zalogowany na zadne konto')

    session.pop('id', None)
    session.pop('username', None)

    return render_template('index.html', msg ='Wylogowanie przebieglo pomyslnie')

@app.route('/dodajOferte', methods=['GET', 'POST'])
def dodawanieOferty():
    if not session:
        return render_template('index.html', msg ='Zaloguj sie lub utworz konto, by dodac oferte')

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
        return render_template('index.html', msg ='Zaloguj sie, by zobaczyc swoje oferty')    
    
    if request.method == 'POST':
        usunOferte = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        usunOferte.execute('DELETE FROM oferta WHERE ID_oferty = % s', (str(request.form.get('usun'))))

        mysql.connection.commit()
        return render_template('index.html' ,msg= 'Oferta zostala usunieta' ,listaOfert=listaOfert('ANY'))

    return render_template('mojeOferty.html' ,listaOfert=listaOfert(session['id']))

@app.route('/mojeDane', methods=['GET', 'POST'])
def mojeDane():
    if not session:
        return render_template('index.html', msg ='Zaloguj sie, by zobaczyc swoje dane')

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

@app.errorhandler(429)
@limiter.limit("2/day")
def ratelimit_handler():
  return "Przekroczyles limit zadan"



if __name__ == '__main__':
    app.run('0.0.0.0', 4449)