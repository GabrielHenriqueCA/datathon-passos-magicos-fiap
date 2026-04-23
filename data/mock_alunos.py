USERS = {
    'admin':   {'password': 'admin123', 'role': 'admin', 'aluno_key': None},
    'aluno01': {'password': '1234',     'role': 'aluno', 'aluno_key': 'aluno01'},
    'aluno02': {'password': '1234',     'role': 'aluno', 'aluno_key': 'aluno02'},
    'aluno03': {'password': '1234',     'role': 'aluno', 'aluno_key': 'aluno03'},
}

ALUNOS_MOCK = {
    'aluno01': {
        'nome': 'Ana Silva', 'ra': 'PM001', 'pedra': 'Ametista',
        'fase': 5, 'anos_programa': 3,
        'inde': 7.52, 'ida': 7.8, 'ieg': 8.1, 'iaa': 7.2, 'ips': 6.9, 'ipv': 7.5,
        'nota_mat': 7.5, 'nota_port': 8.0, 'nota_ing': 6.5,
        'historico_inde': {2022: 6.1, 2023: 6.8, 2024: 7.52},
    },
    'aluno02': {
        'nome': 'Bruno Santos', 'ra': 'PM002', 'pedra': 'Quartzo',
        'fase': 2, 'anos_programa': 1,
        'inde': 4.8, 'ida': 4.5, 'ieg': 4.2, 'iaa': 5.1, 'ips': 4.8, 'ipv': 3.9,
        'nota_mat': 4.0, 'nota_port': 5.0, 'nota_ing': 0.0,
        'historico_inde': {2023: 4.2, 2024: 4.8},
    },
    'aluno03': {
        'nome': 'Carla Oliveira', 'ra': 'PM003', 'pedra': 'Topázio',
        'fase': 7, 'anos_programa': 5,
        'inde': 8.9, 'ida': 9.1, 'ieg': 9.3, 'iaa': 8.7, 'ips': 8.5, 'ipv': 9.0,
        'nota_mat': 9.0, 'nota_port': 9.2, 'nota_ing': 8.5,
        'historico_inde': {2020: 6.5, 2021: 7.2, 2022: 7.9, 2023: 8.4, 2024: 8.9},
    },
}
